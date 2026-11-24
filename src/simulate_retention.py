"""SIMULATED data for "Brand G", a fictional collagen D2C brand (seed 42). Never Glow25's numbers.

Calibrated on public facts only: real product types and prices, real subscription discounts (-15 % monthly,
-25 % every 3 months), market weights from Eurostat isoc_ec_ibgs, a January peak from Wikipedia pageviews and
a 30-day jar (450 g / 15 g servings). Everything else is an assumption listed in docs/assumptions.md.

Period 2024-11-01 -> 2026-10-31. Timestamps are UTC; reports use Europe/Berlin.
Writes data/sim/*.parquet and data/_hidden_truth.csv (the planted events, removed before publishing).

    python src/simulate_retention.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUB, SIM = ROOT / "data" / "public", ROOT / "data" / "sim"
rng = np.random.default_rng(42)
START, END = pd.Timestamp("2024-11-01"), pd.Timestamp("2026-10-31 23:59:59")
N_CUST = 120_000
DAY = pd.Timedelta(days=1)
PRICE_UP = pd.Timestamp("2026-04-01")          # event 5: subscription price +10 %
MPP_FROM = pd.Timestamp("2025-09-01")          # event 7: machine opens recorded from here
WINBACK_LAUNCH = pd.Timestamp("2026-01-02")    # event 3
J26_TEST = (pd.Timestamp("2026-02-01"), pd.Timestamp("2026-05-31 23:59:59"))   # event 2: J21 vs J26 A/B
FR_TEST = (pd.Timestamp("2025-03-01"), pd.Timestamp("2026-02-28 23:59:59"))    # localisation test
ENERGY_LAUNCH = pd.Timestamp("2025-10-07")

PRODUCTS = pd.DataFrame([
    ("P01", "Collagen powder with vitamin C, 450 g", "powder", 29.99, True, 30, 6.90),
    ("P02", "Collagen Plus powder, 450 g", "powder", 39.99, True, 30, 8.90),
    ("P03", "Collagen Intensiv sticks", "sticks", 49.99, True, 30, 11.00),
    ("P04", "Collagen drink ampoules", "ampoules", 59.99, True, 30, 14.50),
    ("P05", "Trial pack original, 225 g", "trial", 14.99, False, 15, 3.60),
    ("P06", "Trial pack Plus, 225 g", "trial", 19.99, False, 15, 4.60),
    ("P07", "Balance capsules", "capsules", 34.99, True, 30, 7.40),
    ("P08", "Energy powder", "powder", 34.99, True, 30, 7.80),
    ("P09", "Beginner bundle", "bundle", 27.99, False, 15, 6.60),
    ("P10", "Routine bundle", "bundle", 59.99, False, 30, 14.80),
    ("P11", "Body cream, 200 ml", "cosmetic", 41.99, False, 60, 8.60),
    ("P12", "Eye pads", "cosmetic", 24.49, False, 60, 5.20),
], columns=["product_id", "name", "type", "price_eur", "subscribable", "supply_days", "unit_cogs_eur"])
PI = {p: i for i, p in enumerate(PRODUCTS.product_id)}
PRICE = PRODUCTS.price_eur.to_numpy()
COGS = PRODUCTS.unit_cogs_eur.to_numpy()
SUPPLY = PRODUCTS.supply_days.to_numpy()
SUBABLE = PRODUCTS.subscribable.to_numpy()
JAR = np.isin(PRODUCTS.product_id, ["P01", "P02", "P03", "P04", "P07", "P08"])
MKTS = np.array(["DE", "AT", "FR", "BE", "IT", "NL", "ES", "GB"])
SHIP = {"DE": 4.20, "AT": 5.40, "FR": 5.90, "BE": 5.60, "IT": 6.20, "NL": 5.60, "ES": 6.20, "GB": 7.80}
SHIP_A = np.array([SHIP[m] for m in MKTS])
CHANNELS = np.array(["paid_social", "paid_search", "influencer", "organic_direct", "referral"])
FLOW_IDS = ["F1_welcome", "F2_education", "F3_trial_to_sub", "F4_replenishment", "F5_sub_onboarding",
            "F6_cancel_save", "F7_winback", "F8_vip_loyalty"]


def logistic(x):
    return 1 / (1 + np.exp(-x))


_DRAWS: dict[int, np.ndarray] = {}


def _draw(salt: int) -> np.ndarray:
    """One fixed uniform number per customer and salt: assignments are deterministic and independent across flows."""
    if salt not in _DRAWS:
        _DRAWS[salt] = np.random.default_rng(10_000 + salt).random(200_000)
    return _DRAWS[salt]


def holdout(cidx, flow_no):
    """Permanent 10 % holdout per customer and flow (independent draw for every flow)."""
    return _draw(flow_no)[np.asarray(cidx, np.int64)] < 0.10


def ab_split(cidx, salt):
    return _draw(100 + salt)[np.asarray(cidx, np.int64)] < 0.5


# ------------------------------------------------------------------ calibration from public data
def season_index():
    w = pd.read_csv(PUB / "wikipedia_collagen_pageviews.csv", dtype={"month": str})
    w["m"] = w.month.str[4:6].astype(int)
    w["norm"] = w.views / w.groupby("project").views.transform("mean")
    idx = w.groupby("m").norm.mean()
    return (idx / idx.mean()).to_dict()


def market_weights():
    e = pd.read_csv(PUB / "eurostat_isoc_ec_ibgs.csv")
    f = e[e.ind_type == "F_Y25_54"].pivot_table(index="geo", columns="indic_is", values="value")
    prop = (f.I_BMED1 * f.I_BCBW / 100).to_dict()
    prop["GB"] = prop["DE"]                                    # no Eurostat value for the UK: DE used
    size = {"DE": 1.0, "AT": 0.11, "FR": 0.80, "BE": 0.14, "IT": 0.72, "NL": 0.21, "ES": 0.60, "GB": 0.80}
    home = {"DE": 2.2, "AT": 1.6}                              # home-market premium (assumption)
    w = np.array([prop[m] * size[m] * home.get(m, 1.0) for m in MKTS])
    return w / w.sum()


SEASON = season_index()
JAN_DEC = 1.55                                               # reactivation hazard, January vs December
G = np.log(JAN_DEC) / np.log(SEASON[1] / SEASON[12])
REACT_MULT = {m: (SEASON[m] / SEASON[12]) ** G for m in range(1, 13)}


# ------------------------------------------------------------------ customers and first orders
def make_customers():
    months = pd.period_range("2024-11", "2026-10", freq="M")
    w = np.array([SEASON[m.month] * 1.012 ** i * (1.30 if m.month == 11 else 1.0) for i, m in enumerate(months)])
    n_m = rng.multinomial(N_CUST, w / w.sum())
    days = []
    for m, n in zip(months, n_m):
        start, nd = m.start_time, m.days_in_month
        d = rng.integers(0, nd, n).astype(float)
        if m.month == 11:                                      # Black Friday week
            bf = rng.random(n) < 0.35
            d[bf] = nd - 7 + rng.integers(0, 7, bf.sum())
        days.append(start + pd.to_timedelta(d, unit="D"))
    local = pd.DatetimeIndex(np.concatenate([x.values for x in days]))
    hw = np.array([1, .6, .4, .3, .3, .4, .8, 1.5, 2.5, 3, 3.2, 3.4, 3.6, 3.4, 3.3, 3.4, 3.6, 4, 4.6, 5.4, 6, 5.5, 4, 2.2])
    hour = rng.choice(np.arange(24), len(local), p=hw / hw.sum())
    local = local + pd.to_timedelta(hour * 3600 + rng.integers(0, 3600, len(local)), unit="s")
    ts = local.tz_localize("Europe/Berlin", ambiguous=False, nonexistent="shift_forward").tz_convert("UTC").tz_localize(None)
    order = np.argsort(ts.values)
    ts = ts[order]
    n = len(ts)
    mk = rng.choice(len(MKTS), n, p=market_weights())
    ch = rng.choice(len(CHANNELS), n, p=[.38, .18, .16, .20, .08])
    z = rng.normal(0, 1, n) + np.array([0, .05, -.25, .15, .30])[ch]
    # first product: FR leans to beauty (cosmetics, bundles), in line with Eurostat (beauty >> supplements online)
    base = np.array([.26, .14, .05, .04, .18, .08, .04, .03, .07, .04, .04, .03])
    fr = np.array([.20, .12, .04, .03, .16, .07, .03, .03, .08, .07, .10, .07])
    p0 = np.empty(n, int)
    for is_fr, probs in ((False, base), (True, fr)):
        sel = (MKTS[mk] == "FR") == is_fr
        p0[sel] = rng.choice(12, sel.sum(), p=probs / probs.sum())
    p0[(p0 == PI["P08"]) & (ts < ENERGY_LAUNCH)] = PI["P01"]
    cust = pd.DataFrame({
        "cidx": np.arange(n), "customer_id": [f"C{i + 1:06d}" for i in range(n)], "market": MKTS[mk],
        "first_order_ts": ts, "acquisition_channel": CHANNELS[ch],
        "consent_email": rng.random(n) < 0.82, "consent_sms": rng.random(n) < 0.28,
        "email_hash": [f"{x:016x}" for x in rng.integers(0, 2 ** 62, n)]})
    return cust, z, p0, mk


# ------------------------------------------------------------------ order economics
class Book:
    """Collects orders, lines and loyalty events."""

    def __init__(self):
        self.orders, self.lines = [], []
        self.next_id = 1

    def add(self, cidx, ts, prod, qty, kind, disc_rate, sub_id=None, addon=None, campaign=None, source="base"):
        n = len(cidx)
        if n == 0:
            return np.array([], int)
        ids = np.arange(self.next_id, self.next_id + n)
        self.next_id += n
        gross_main = PRICE[prod] * qty
        ts = np.asarray(ts, "datetime64[ns]")
        price_mult = np.where(ts >= PRICE_UP.to_datetime64(), 1.10, 1.0) if kind == "sub" else np.ones(n)
        gross_main = np.round(gross_main * price_mult, 2)
        addon = np.full(n, -1) if addon is None else addon
        gross_add = np.where(addon >= 0, PRICE[np.maximum(addon, 0)], 0.0)
        disc = np.round(gross_main * disc_rate, 2)
        cogs = COGS[prod] * qty + np.where(addon >= 0, COGS[np.maximum(addon, 0)], 0)
        self.orders.append(pd.DataFrame({"order_no": ids, "cidx": cidx, "ts_utc": ts, "prod": prod, "qty": qty,
                                         "is_subscription": kind == "sub",
                                         "sub_id": sub_id if sub_id is not None else -1, "gross_eur": gross_main + gross_add,
                                         "discount_eur": disc, "cogs_eur": np.round(cogs, 2), "campaign": campaign,
                                         "source": source}))
        ln = pd.DataFrame({"order_no": ids, "product_id": PRODUCTS.product_id.to_numpy()[prod], "qty": qty,
                           "unit_price_eur": np.round(PRICE[prod] * price_mult, 2), "line_gross_eur": gross_main})
        la = pd.DataFrame({"order_no": ids, "product_id": PRODUCTS.product_id.to_numpy()[np.maximum(addon, 0)], "qty": 1,
                           "unit_price_eur": gross_add, "line_gross_eur": gross_add})[addon >= 0]
        self.lines += [ln, la]
        return ids


# ------------------------------------------------------------------ one-off repurchase chains
def next_product(prev):
    out = prev.copy()
    t = PRODUCTS.type.to_numpy()[prev]
    trial = np.isin(t, ["trial", "bundle"])
    out[trial] = np.where(rng.random(trial.sum()) < 0.7, PI["P01"], PI["P02"])
    cos = t == "cosmetic"
    out[cos] = np.where(rng.random(cos.sum()) < 0.5, prev[cos], PI["P01"])
    sw = (~trial & ~cos) & (rng.random(len(prev)) < 0.12)
    out[sw] = rng.choice([PI["P01"], PI["P02"], PI["P03"], PI["P07"]], sw.sum())
    return out


def run_chains(book, st, cidx, t, prod, k, allow_sub=True):
    """Vectorised rounds: after each one-off order, does the customer reorder, when, and as what."""
    cidx, t, prod, k = map(np.asarray, (cidx, t, prod, k))
    while len(cidx):
        member = st["member_since"][cidx] <= t
        lp = (-0.75 + 0.95 * st["z"][cidx] + 0.30 * np.minimum(k - 1, 3) + np.where(JAR[prod], 0.25, 0)
              - np.where(PRODUCTS.type.to_numpy()[prod] == "cosmetic", 0.4, 0) - np.where(np.isin(st["mk"][cidx], [7]), 0.15, 0))
        p = logistic(lp) * np.where(member, 1.05, 1.0)
        cont = rng.random(len(cidx)) < np.minimum(p, 0.97)
        gap = SUPPLY[prod] + rng.gamma(3, 2.0, len(cidx)) - 2.5
        late = rng.random(len(cidx)) < 0.28
        gap = gap + np.where(late, rng.exponential(45, len(cidx)), 0)
        t_next = t + pd.to_timedelta(gap * 86400, unit="s").values
        ok = cont & (t_next <= END.to_datetime64())
        # chain ends: remember last one-off order
        st["chain_end"][cidx[~ok]] = t[~ok]
        cidx, t_next, prod, k = cidx[ok], t_next[ok], prod[ok], k[ok] + 1
        nprod = next_product(prod)
        to_sub = allow_sub & SUBABLE[nprod] & (rng.random(len(cidx)) < 0.10)
        st["sub_starts"].append(pd.DataFrame({"cidx": cidx[to_sub], "ts": t_next[to_sub], "prod": nprod[to_sub],
                                              "origin": "reorder_conversion"}))
        st["chain_end"][cidx[to_sub]] = t_next[to_sub]
        stay = ~to_sub
        cidx, t, prod, k = cidx[stay], t_next[stay], nprod[stay], k[stay]
        book.add(cidx, t, prod, np.ones(len(cidx), int), "oneoff", np.zeros(len(cidx)))
        loyalty_join(st, cidx, t, k)


def loyalty_join(st, cidx, t, k):
    """Self-selection: repeat buyers (observable) and engaged customers (latent, weaker) join more often."""
    free = st["member_since"][cidx] > t
    lp = -3.3 + 0.55 * np.minimum(k, 5) + 0.05 * st["z"][cidx]
    j = free & (rng.random(len(cidx)) < logistic(lp))
    st["member_since"][cidx[j]] = t[j]


# ------------------------------------------------------------------ subscriptions
def cancel_curve(base, n, decay, amp):
    return base * (1 + amp * np.exp(-np.arange(n) / decay))


def solve_base(target, n_points, decay, amp, save_avg, fail=0.011):
    lo, hi = 0.0, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        s = np.prod(1 - cancel_curve(mid, n_points, decay, amp) * (1 - save_avg) - fail)
        lo, hi = (mid, hi) if s > target else (lo, mid)
    return mid


SAVE_T, SAVE_H = 0.32, 0.08                                  # cancel-save flow vs its holdout
SAVE_AVG = 0.9 * SAVE_T + 0.1 * SAVE_H
BASE_M = solve_base(0.41, 12, 2.5, 5.0, SAVE_AVG, fail=0.007)          # event 4: 12-month retention monthly 41 %
BASE_Q = solve_base(0.58, 4, 1.5, 2.0, SAVE_AVG, fail=0.007)           # quarterly 58 %
REASONS = np.array(["too_expensive", "have_too_much", "not_for_me", "switching_brand", "other"])
REASON_P = np.array([.30, .24, .20, .09, .17])


def simulate_subs(book, st, starts: pd.DataFrame):
    """One row per subscription; one charge per scheduled date; orders for successful charges."""
    if starts is None or len(starts) == 0:
        return
    s = starts.reset_index(drop=True)
    n = len(s)
    sid0 = st["next_sub"]
    st["next_sub"] += n
    sid = np.arange(sid0, sid0 + n)
    cidx = s.cidx.to_numpy()
    mk = st["mk"][cidx]
    is_wb = (s.origin == "winback_offer").to_numpy()
    quarterly = (rng.random(n) < np.where(is_wb, 0.0, 0.35))
    interval = np.where(quarterly, 3, 1)
    disc = np.where(quarterly, 0.25, 0.15)
    qty = np.where(quarterly, 3, 1)
    prod = s["prod"].to_numpy().copy()
    created = pd.DatetimeIndex(s.ts)
    local_date = created.normalize()
    onboard_t = ~holdout(cidx, 5)
    save_t = ~holdout(cidx, 6)
    rows_sub = dict(subscription_id=sid, cidx=cidx, product=PRODUCTS.product_id.to_numpy()[prod], interval=np.where(quarterly, "3M", "1M"),
                    discount=np.where(quarterly, 25, 15), created=created, origin=s.origin.to_numpy())
    cancelled = np.full(n, np.datetime64("NaT"), "datetime64[ns]")
    reason = np.full(n, None, object)
    skips, swaps = np.zeros(n, int), np.zeros(n, int)
    # first charge = the order that created the subscription
    first_disc = np.where(is_wb, 0.30, disc)
    oid = book.add(cidx, created.values, prod, qty, "sub", first_disc, sub_id=sid)
    charges = [pd.DataFrame({"subscription_id": sid, "scheduled_date": local_date, "status": "success", "order_no": oid,
                             "charge_no": 1})]
    active = np.ones(n, bool)
    k = np.ones(n, int)                                        # charges done
    nxt = local_date + pd.to_timedelta(interval * 30, unit="D")
    nxt = nxt.values
    skip_next = np.zeros(n, int)
    while active.any():
        a = np.where(active & (nxt <= END.normalize().to_datetime64()))[0]
        active[active & (nxt > END.normalize().to_datetime64())] = False
        if len(a) == 0:
            break
        when = pd.DatetimeIndex(nxt[a])
        # cancel intent before this charge
        q = quarterly[a]
        kk = k[a] - 1
        h = np.where(q, BASE_Q * (1 + 2.0 * np.exp(-kk / 1.5)), BASE_M * (1 + 5.0 * np.exp(-kk / 2.5)))
        h = h * np.where(onboard_t[a] & (kk < 3), 0.92, 1.0) * np.where(is_wb[a], 2.0, 1.0)
        after = when >= PRICE_UP
        te_mult = np.where(after & np.isin(mk[a], [2, 4]), 2.4, np.where(after, 1.1, 1.0))   # FR, IT
        h = h * (1 + REASON_P[0] * (te_mult - 1))
        intent = rng.random(len(a)) < h
        p_te = REASON_P[0] * te_mult / (REASON_P[0] * te_mult + REASON_P[1:].sum())
        r = np.where(rng.random(len(a)) < p_te, 0, 1 + rng.choice(4, len(a), p=REASON_P[1:] / REASON_P[1:].sum()))
        saved = intent & (rng.random(len(a)) < np.where(save_t[a], SAVE_T, SAVE_H)) & (r != 3)
        cancel = intent & ~saved
        cdate = when - pd.to_timedelta(rng.integers(1, 6, len(a)), unit="D")
        ci = a[cancel]
        cancelled[ci] = cdate.values[cancel]
        reason[ci] = REASONS[r[cancel]]
        active[ci] = False
        st["sub_end"][cidx[ci]] = np.maximum(st["sub_end"][cidx[ci]], cdate.values[cancel])
        st["cancel_events"].append(pd.DataFrame({"cidx": cidx[ci], "ts": cdate.values[cancel], "reason": REASONS[r[cancel]],
                                                 "subscription_id": sid[ci], "intent_saved": False}))
        # saved: skip (55 %), swap (30 %), pause = 2 skips (15 %)
        sv = a[saved]
        how = rng.choice(3, len(sv), p=[.55, .30, .15])
        skip_next[sv[how == 0]] = 1
        skip_next[sv[how == 2]] = 2
        sw = sv[how == 1]
        swaps[sw] += 1
        prod[sw] = np.where(prod[sw] == PI["P01"], PI["P02"], PI["P01"])
        st["cancel_events"].append(pd.DataFrame({"cidx": cidx[sv], "ts": cdate.values[saved], "reason": "saved",
                                                 "subscription_id": sid[sv], "intent_saved": True}))
        go = a[~cancel]
        w2 = pd.DatetimeIndex(nxt[go])
        voluntary_skip = rng.random(len(go)) < np.where(quarterly[go], 0.17, 0.012)
        do_skip = (skip_next[go] > 0) | voluntary_skip
        skip_next[go] = np.maximum(skip_next[go] - 1, 0)
        skips[go[do_skip]] += 1
        rec = go[~do_skip]
        fail = rng.random(len(rec)) < 0.02
        retried_ok = fail & (rng.random(len(rec)) < 0.65)
        final_fail = fail & ~retried_ok
        ok = rec[~final_fail]
        when_ok = pd.DatetimeIndex(nxt[ok])
        # processed at 00:05-00:59 Berlin time on the scheduled date (UTC: previous evening)
        ts_local = when_ok + pd.to_timedelta(rng.integers(300, 3540, len(ok)), unit="s") + pd.to_timedelta(
            np.where(retried_ok[~final_fail], 3, 0), unit="D")
        ts_utc = ts_local.tz_localize("Europe/Berlin", ambiguous=False, nonexistent="shift_forward").tz_convert("UTC").tz_localize(None)
        addon = np.where(rng.random(len(ok)) < np.where(quarterly[ok], 0.05, 0.20),
                         rng.choice([PI["P11"], PI["P12"], PI["P07"], PI["P10"]], len(ok)), -1)
        wb_disc = is_wb[ok] & (k[ok] < 6)
        oid = book.add(cidx[ok], ts_utc.values, prod[ok], qty[ok], "sub", np.where(wb_disc, 0.30, disc[ok]), sub_id=sid[ok], addon=addon)
        charges.append(pd.DataFrame({"subscription_id": sid[go[do_skip]], "scheduled_date": nxt[go[do_skip]], "status": "skipped",
                                     "order_no": -1, "charge_no": k[go[do_skip]] + 1}))
        charges.append(pd.DataFrame({"subscription_id": sid[ok], "scheduled_date": nxt[ok],
                                     "status": np.where(retried_ok[~final_fail], "retried", "success"), "order_no": oid,
                                     "charge_no": k[ok] + 1}))
        ff = rec[final_fail]
        charges.append(pd.DataFrame({"subscription_id": sid[ff], "scheduled_date": nxt[ff], "status": "failed", "order_no": -1,
                                     "charge_no": k[ff] + 1}))
        fdate = (pd.DatetimeIndex(nxt[ff]) + pd.Timedelta(days=7)).values
        cancelled[ff] = fdate
        reason[ff] = "payment_failed"
        active[ff] = False
        st["sub_end"][cidx[ff]] = np.maximum(st["sub_end"][cidx[ff]], fdate)
        k[ok] += 1
        nxt[go] = (pd.DatetimeIndex(nxt[go]) + pd.to_timedelta(interval[go] * 30, unit="D")).values
    st["subs"].append(pd.DataFrame({**rows_sub, "cancelled": cancelled, "cancel_reason": reason, "skips": skips, "swaps": swaps}))
    st["charges"] += charges
    still = np.isnat(cancelled)
    st["sub_end"][cidx[still]] = END.to_datetime64()


# ------------------------------------------------------------------ main generation
def generate():
    cust, z, p0, mk = make_customers()
    n = len(cust)
    nat = np.datetime64("NaT")
    st = {"z": z, "mk": mk, "member_since": np.full(n, np.datetime64("2100-01-01"), "datetime64[ns]"),
          "chain_end": np.full(n, nat, "datetime64[ns]"), "sub_end": np.full(n, np.datetime64("1900-01-01"), "datetime64[ns]"),
          "sub_starts": [], "subs": [], "charges": [], "cancel_events": [], "next_sub": 1}
    book = Book()
    t0 = cust.first_order_ts.values
    cidx = cust.cidx.to_numpy()
    sub_first = SUBABLE[p0] & (rng.random(n) < np.where(np.isin(mk, [2, 4]), 0.15, 0.20))
    st["sub_starts"].append(pd.DataFrame({"cidx": cidx[sub_first], "ts": t0[sub_first], "prod": p0[sub_first], "origin": "first_order"}))
    one = ~sub_first
    book.add(cidx[one], t0[one], p0[one], np.ones(one.sum(), int), "oneoff", np.zeros(one.sum()))
    st["member_since"][:] = np.datetime64("2100-01-01")
    loyalty_join(st, cidx[one], t0[one], np.ones(one.sum(), int))
    # trial -> subscription flow (F3): trial buyers with consent; base 8 %, +5 pts when treated
    trial = one & np.isin(PRODUCTS.type.to_numpy()[p0], ["trial", "bundle"]) & np.isin(p0, [PI["P05"], PI["P06"], PI["P09"]])
    elig = trial & cust.consent_email.to_numpy()
    p_conv = np.where(elig, 0.08 + 0.05 * ~holdout(cidx, 3), 0.08)
    conv = trial & (rng.random(n) < p_conv)
    conv_ts = t0 + pd.to_timedelta(rng.uniform(9, 20, n) * 86400, unit="s").values
    conv &= conv_ts <= END.to_datetime64()
    st["sub_starts"].append(pd.DataFrame({"cidx": cidx[conv], "ts": conv_ts[conv],
                                          "prod": np.where(p0[conv] == PI["P06"], PI["P02"], PI["P01"]), "origin": "trial_flow"}))
    st["chain_end"][cidx[conv]] = conv_ts[conv]
    ch = one & ~conv
    run_chains(book, st, cidx[ch], t0[ch], p0[ch], np.ones(ch.sum(), int))
    simulate_subs(book, st, pd.concat(st["sub_starts"], ignore_index=True))
    st["sub_starts"] = []
    # reactivation of lapsed customers, month by month (seasonal: January = 1.38 x December)
    for m in pd.period_range("2025-02", "2026-10", freq="M"):
        ms = m.start_time.to_datetime64()
        last = np.fmax(st["chain_end"], st["sub_end"])
        lapsed = (last <= ms - np.timedelta64(90, "D")) & (st["sub_end"] < ms)
        idx = np.where(lapsed)[0]
        p = 0.021 * REACT_MULT[m.month] * np.exp(0.35 * st["z"][idx]) / np.exp(0.35 ** 2 / 2)
        r = idx[rng.random(len(idx)) < p]
        ts = ms + (rng.uniform(0, m.days_in_month, len(r)) * 86400).astype("timedelta64[s]")
        prod = rng.choice([PI["P01"], PI["P02"], PI["P05"], PI["P03"], PI["P11"]], len(r), p=[.45, .2, .15, .1, .1])
        book.add(r, ts, prod, np.ones(len(r), int), "oneoff", np.zeros(len(r)), source="reactivation")
        st["chain_end"][r] = ts
        run_chains(book, st, r, ts, prod, np.full(len(r), 2))
        new = pd.concat(st["sub_starts"], ignore_index=True) if st["sub_starts"] else None
        st["sub_starts"] = []
        simulate_subs(book, st, new)
    # -30 % win-back offer to "too expensive" cancellers (event 5): 18 % come back vs 11 % in the holdout
    ce = pd.concat(st["cancel_events"], ignore_index=True)
    te = ce[(ce.reason == "too_expensive") & (ce.ts >= pd.Timestamp("2024-12-01"))].drop_duplicates("cidx")
    te = te.assign(offer_ts=te.ts + pd.Timedelta(days=7))
    te = te[te.offer_ts <= END - pd.Timedelta(days=20)]
    hold = holdout(te.cidx.to_numpy(), 9)
    back = rng.random(len(te)) < np.where(hold, 0.14, 0.18)
    back_ts = te.offer_ts.values + (rng.uniform(1, 20, len(te)) * 86400).astype("timedelta64[s]")
    wb = pd.DataFrame({"cidx": te.cidx.to_numpy()[back], "ts": back_ts[back], "prod": PI["P01"],
                       "origin": np.where(hold[back], "returned_no_offer", "winback_offer")})
    simulate_subs(book, st, wb)
    st["winback30"] = te.assign(holdout_flag=hold, returned=back)
    return cust, book, st


# ------------------------------------------------------------------ flows, campaigns, email events
def orders_frame(book):
    o = pd.concat(book.orders, ignore_index=True).sort_values(["ts_utc", "order_no"]).reset_index(drop=True)
    return o


def entries_education(cust, o):
    first = o.sort_values("ts_utc").drop_duplicates("cidx")
    e = first[(~first.is_subscription) & cust.consent_email.to_numpy()[first.cidx]]
    return pd.DataFrame({"cidx": e.cidx, "entry_ts": e.ts_utc, "flow": "F2_education", "variant": "standard"})


def entries_replenishment(cust, o, subs):
    j = o[(~o.is_subscription) & JAR[o["prod"].to_numpy()] & cust.consent_email.to_numpy()[o.cidx]]
    j = j[j.ts_utc <= END - pd.Timedelta(days=21)]
    e = pd.DataFrame({"cidx": j.cidx.to_numpy(), "entry_ts": j.ts_utc.to_numpy(), "flow": "F4_replenishment"})
    in_test = (e.entry_ts >= J26_TEST[0]) & (e.entry_ts <= J26_TEST[1])
    b = ab_split(e.cidx, 2)
    e["variant"] = np.where(e.entry_ts > J26_TEST[1], "J26_branch", np.where(in_test, np.where(b, "J26_branch", "J21"), "J21"))
    return e


def entries_welcome(cust):
    c = cust[cust.consent_email]
    fr = (c.market == "FR") & (c.first_order_ts >= FR_TEST[0]) & (c.first_order_ts <= FR_TEST[1])
    v = np.where(fr, np.where(ab_split(c.cidx, 7), "FR_adapted", "FR_translated"), "standard")
    return pd.DataFrame({"cidx": c.cidx, "entry_ts": c.first_order_ts, "flow": "F1_welcome", "variant": v})


def entries_from_subs(subs, flow):
    s = subs[subs.created.notna()]
    return pd.DataFrame({"cidx": s.cidx, "entry_ts": s.created, "flow": flow, "variant": "standard"})


def entries_winback(cust, o, subs):
    """Lapsed 90 days (no order, no active subscription), from the launch on 2026-01-02 (back-fill of 90-365 days)."""
    o1 = o[["cidx", "ts_utc"]].sort_values(["cidx", "ts_utc"])
    o1["next"] = o1.groupby("cidx").ts_utc.shift(-1)
    o1["lapse_ts"] = o1.ts_utc + pd.Timedelta(days=90)
    gap_ok = o1.next.isna() | (o1.next > o1.lapse_ts)
    e = o1[gap_ok & (o1.lapse_ts <= END - pd.Timedelta(days=30))].copy()
    backfill = (e.lapse_ts < WINBACK_LAUNCH) & (e.lapse_ts >= WINBACK_LAUNCH - pd.Timedelta(days=275)) & (
        e.next.isna() | (e.next > WINBACK_LAUNCH))
    e["entry_ts"] = e.lapse_ts.where(~backfill, WINBACK_LAUNCH + pd.Timedelta(hours=8))
    e = e[(e.entry_ts >= WINBACK_LAUNCH)]
    act = subs[["cidx", "created", "cancelled"]].copy()
    act["cancelled"] = act.cancelled.fillna(END)
    m = e.merge(act, on="cidx", how="left")
    is_active = (m.created <= m.entry_ts) & (m.cancelled > m.entry_ts)
    bad = set(m.loc[is_active, ["cidx", "entry_ts"]].itertuples(index=False, name=None))
    keep = [(c, t) not in bad for c, t in zip(e.cidx, e.entry_ts)]
    e = e[keep & cust.consent_email.to_numpy()[e.cidx]]
    return pd.DataFrame({"cidx": e.cidx, "entry_ts": pd.to_datetime(e.entry_ts), "flow": "F7_winback", "variant": "standard"})


FLOW_STEPS = {  # offsets in days and message names
    "F1_welcome": [(0.02, "W1 welcome & ritual"), (2, "W2 how to use it"), (5, "W3 our story")],
    "F2_education": [(3, "E1 first week"), (10, "E2 build the habit"), (17, "E3 recipes"), (24, "E4 FAQ"), (31, "E5 routine check-in")],
    "F3_trial_to_sub": [(4, "T1 halfway"), (9, "T2 save with a subscription"), (13, "T3 last servings")],
    "F4_replenishment": [(21, "R1 running low?")],
    "F5_sub_onboarding": [(0.05, "S1 welcome to your plan"), (5, "S2 skip, swap, pause"), (20, "S3 next delivery")],
    "F6_cancel_save": [(0.01, "X1 before you go: skip / swap / pause")],
    "F7_winback": [(0, "B1 we miss you"), (10, "B2 what is new"), (25, "B3 comeback offer")],
    "F8_vip_loyalty": [(0, "V1 welcome to Gold"), (-2, "V2 early access")],
}
FLOW_NO = {f: i + 1 for i, f in enumerate(FLOW_IDS)}
EXIT_ON_ORDER = {"F3_trial_to_sub", "F4_replenishment", "F7_winback"}


def build_sends(entries, o):
    """Expand flow entries into sends; holdout entries get a single suppressed row (sent = 0)."""
    out = []
    first_after = o[["cidx", "ts_utc"]].sort_values("ts_utc")
    for flow, e in entries.groupby("flow"):
        e = e.copy()
        e["holdout_flag"] = holdout(e.cidx, FLOW_NO[flow])
        steps = FLOW_STEPS[flow]
        if flow == "F8_vip_loyalty":
            steps = steps[:1]
        h = e[e.holdout_flag].assign(send_ts=e.entry_ts, message="(holdout: suppressed)", sent=False)
        out.append(h)
        t = e[~e.holdout_flag]
        if flow in EXIT_ON_ORDER:
            nxt = pd.merge_asof(t.sort_values("entry_ts"), first_after.rename(columns={"ts_utc": "next_order"}),
                                left_on="entry_ts", right_on="next_order", by="cidx", direction="forward",
                                allow_exact_matches=False)
        else:
            nxt = t.assign(next_order=pd.NaT)
        if flow in EXIT_ON_ORDER:   # intention to treat: entries that exit before the first email stay in the readout
            first_off = np.where(nxt.variant == "J26_branch", 26.0, steps[0][0]) if flow == "F4_replenishment" else steps[0][0]
            first_send = nxt.entry_ts + pd.to_timedelta(np.asarray(first_off, float) * 86400 + 9 * 3600, unit="s")
            gone = nxt[nxt.next_order.notna() & (nxt.next_order <= first_send)]
            out.append(gone.drop(columns="next_order").assign(send_ts=gone.entry_ts, message="(exited before first email)", sent=False))
        for off, msg in steps:
            if flow == "F4_replenishment":
                off_arr = np.where(nxt.variant == "J26_branch", 26.0, 21.0)
            else:
                off_arr = np.full(len(nxt), float(off))
            s = nxt.assign(send_ts=nxt.entry_ts + pd.to_timedelta(off_arr * 86400 + 9 * 3600, unit="s"), message=msg, sent=True)
            if flow == "F4_replenishment":
                s["message"] = np.where(s.variant == "J26_branch", "R1 still have product? (J26)", "R1 running low? (J21)")
            if flow in EXIT_ON_ORDER:
                s = s[s.next_order.isna() | (s.next_order > s.send_ts)]
            out.append(s.drop(columns="next_order"))
            if flow == "F4_replenishment":
                s2 = nxt[(nxt.variant == "J26_branch")]
                s2 = s2.assign(send_ts=s2.entry_ts + pd.Timedelta(days=33, hours=9), message="R2 branch: reminder (J33)", sent=True)
                s2 = s2[(s2.next_order.isna() | (s2.next_order > s2.send_ts)) & (rng.random(len(s2)) < 0.55)]
                out.append(s2.drop(columns="next_order"))
    s = pd.concat(out, ignore_index=True)
    return s[s.send_ts <= END]


CAMPAIGNS = [
    ("2024-11-22", "Black Friday early access (loyalty members)", "black_friday", 0.0, "members"),
    ("2024-11-29", "Black Friday -25%", "black_friday", 0.25, "all"), ("2024-12-02", "Cyber Monday last call", "black_friday", 0.25, "all"),
    ("2024-12-10", "Gift guide", "seasonal", 0.0, "all"), ("2025-01-02", "New year, new ritual -15%", "january", 0.15, "all"),
    ("2025-01-21", "Five ways to build the habit", "content", 0.0, "all"), ("2025-02-11", "Valentine's bundles", "seasonal", 0.0, "all"),
    ("2025-03-12", "Spring routine", "content", 0.0, "all"), ("2025-04-07", "Lemon: early access (Gold)", "launch", 0.0, "gold"),
    ("2025-04-09", "New flavour: Lemon", "launch", 0.0, "all"),
    ("2025-05-06", "Mother's Day gifts", "seasonal", 0.0, "all"), ("2025-06-18", "Summer sale -20%", "sale", 0.20, "all"),
    ("2025-07-16", "Your routine on the go", "content", 0.0, "all"), ("2025-08-20", "Back to routine", "content", 0.0, "all"),
    ("2025-09-10", "Autumn favourites", "content", 0.0, "all"), ("2025-10-05", "Energy powder: early access (Gold)", "launch", 0.0, "gold"),
    ("2025-10-07", "Launch: Energy powder", "launch", 0.0, "all"), ("2025-10-14", "Autumn ritual (subject line test)", "content", 0.0, "all"),
    ("2025-11-21", "Black Friday early access (loyalty members)", "black_friday", 0.0, "members"),
    ("2025-11-28", "Black Friday -25%", "black_friday", 0.25, "all"), ("2025-12-01", "Cyber Monday last call", "black_friday", 0.25, "all"),
    ("2025-12-09", "Gift guide", "seasonal", 0.0, "all"), ("2026-01-02", "New year, new ritual -15%", "january", 0.15, "all"),
    ("2026-01-20", "Five ways to build the habit", "content", 0.0, "all"), ("2026-02-10", "Valentine's bundles", "seasonal", 0.0, "all"),
    ("2026-03-11", "Spring routine", "content", 0.0, "all"), ("2026-04-12", "Mango: early access (Gold)", "launch", 0.0, "gold"),
    ("2026-04-14", "New flavour: Mango", "launch", 0.0, "all"),
    ("2026-05-05", "Mother's Day gifts", "seasonal", 0.0, "all"), ("2026-06-17", "Summer sale -20%", "sale", 0.20, "all"),
    ("2026-07-15", "Your routine on the go", "content", 0.0, "all"), ("2026-08-19", "Back to routine", "content", 0.0, "all"),
    ("2026-09-09", "Autumn favourites", "content", 0.0, "all"), ("2026-10-13", "Autumn ritual", "content", 0.0, "all"),
]


def campaign_recipients(cust, o, member_since, gold_since):
    rows = []
    ot = o[["cidx", "ts_utc"]]
    consent = cust.consent_email.to_numpy()
    for i, (d, name, kind, disc, seg) in enumerate(CAMPAIGNS):
        ts = pd.Timestamp(d) + pd.Timedelta(hours=8)
        act = ot[(ot.ts_utc < ts) & (ot.ts_utc >= ts - pd.Timedelta(days=365))].cidx.unique()
        act = act[consent[act]]
        if seg == "members":
            act = act[member_since[act] <= ts.to_datetime64()]
        if seg == "gold":
            act = act[gold_since[act] <= ts.to_datetime64()]
        flow_or_campaign = f"CMP{i + 1:02d} {name}"
        v = np.where(ab_split(act, 11), "B", "A") if "subject line test" in name else np.full(len(act), "standard")
        hold = holdout(act, 8) if seg == "gold" else np.zeros(len(act), bool)     # VIP early access keeps a 10 % holdout
        rows.append(pd.DataFrame({"cidx": act, "entry_ts": ts, "flow": flow_or_campaign, "variant": v, "send_ts": ts,
                                  "message": name, "sent": ~hold, "holdout_flag": hold, "kind": kind, "disc": disc}))
    return pd.concat(rows, ignore_index=True)


def engagement(sends, o, z, apple, q_tied, base_click, open_base, rng_):
    """Opens, clicks, bounces and unsubscribes. Clicks are more likely just before an order the customer places
    anyway (that is what makes last-touch attribution claim revenue it did not cause)."""
    s = sends.sort_values("send_ts").reset_index(drop=True)
    nx = pd.merge_asof(s[["cidx", "send_ts"]].reset_index(), o[["cidx", "ts_utc", "gross_eur"]].sort_values("ts_utc"),
                       left_on="send_ts", right_on="ts_utc", by="cidx", direction="forward", allow_exact_matches=False)
    nx = nx.set_index("index").reindex(s.index)
    gap = (nx.ts_utc - s.send_ts).dt.total_seconds() / 86400
    tied = (gap <= 5).to_numpy()
    sent = s.sent.to_numpy()
    zz = z[s.cidx]
    n = len(s)
    bounced = sent & (rng_.random(n) < 0.007)
    delivered = sent & ~bounced
    p_open = logistic(open_base.reindex(s.flow).fillna(-0.5).to_numpy() + 0.55 * zz)
    is_b = (s.variant == "B").to_numpy()
    p_open = np.where(is_b, np.minimum(p_open * 1.16, 0.95), p_open)          # curiosity subject line: more opens
    genuine = delivered & (rng_.random(n) < p_open)
    q = q_tied.reindex(s.flow).fillna(0.15).to_numpy()
    c = base_click.reindex(s.flow).fillna(0.03).to_numpy() * np.exp(0.3 * zz) * np.where(is_b, 0.86, 1.0)
    click = delivered & np.where(tied, rng_.random(n) < q, genuine & (rng_.random(n) < c / np.maximum(p_open, 0.05)))
    genuine |= click
    machine = delivered & ~genuine & apple[s.cidx] & (s.send_ts >= MPP_FROM).to_numpy()
    open_ts = s.send_ts + pd.to_timedelta(np.where(machine, rng_.uniform(60, 900, n), rng_.exponential(5 * 3600, n)), unit="s")
    order_ts = nx.ts_utc
    frac = rng_.uniform(0.05, 0.95, n)
    tied_click_ts = s.send_ts + (order_ts - s.send_ts) * frac
    click_ts = np.where(tied & click, tied_click_ts, open_ts + pd.to_timedelta(rng_.exponential(600, n), unit="s"))
    unsub_p = np.where(s.flow.str.startswith("CMP"), 0.0022, 0.0035)
    unsub_p = np.where(s.variant == "FR_translated", 0.0150, np.where(s.variant == "FR_adapted", 0.0120, unsub_p))
    unsub = delivered & (rng_.random(n) < unsub_p)
    s["delivered"], s["bounced"] = delivered, bounced
    s["opened"], s["open_ts"] = genuine | machine, pd.Series(open_ts).where(genuine | machine)
    s["clicked"], s["click_ts"] = click, pd.Series(pd.to_datetime(click_ts)).where(click)
    s["mpp_flag"], s["unsubscribed"] = machine, unsub
    return s


def attribute(o, ev):
    """Klaviyo-style last touch: last click within 5 days before the order, else last open within 1 day."""
    con = duckdb.connect()
    con.register("o", o[["order_no", "cidx", "ts_utc", "gross_eur", "discount_eur"]])
    con.register("c", ev.loc[ev.clicked, ["cidx", "click_ts", "flow", "send_id"]].rename(columns={"click_ts": "t"}))
    con.register("p", ev.loc[ev.opened, ["cidx", "open_ts", "flow", "send_id"]].rename(columns={"open_ts": "t"}))
    q = """
    with ck as (select o.order_no, c.flow, c.send_id, c.t from o asof join c on o.cidx = c.cidx and o.ts_utc >= c.t
                where o.ts_utc - c.t <= interval 5 day),
         op as (select o.order_no, p.flow, p.send_id, p.t from o asof join p on o.cidx = p.cidx and o.ts_utc >= p.t
                where o.ts_utc - p.t <= interval 1 day)
    select o.order_no, coalesce(ck.flow, op.flow) as flow_or_campaign, coalesce(ck.send_id, op.send_id) as send_id,
           case when ck.order_no is not null then 'click_5d' else 'open_1d' end as touch,
           o.gross_eur - o.discount_eur as attributed_revenue_eur
    from o left join ck using (order_no) left join op using (order_no)
    where ck.order_no is not null or op.order_no is not null"""
    return con.execute(q).df()


def add_incremental(book, o, ev, flow, n_orders, extra_click_window=3.0, variant=None, window=60):
    """Incremental orders caused by a flow: placed by treated recipients who would not have bought in the
    flow window, shortly after a click on a send."""
    cand = ev[(ev.flow == flow) & ev.delivered]
    if variant is not None:
        cand = cand[cand.variant == variant]
    if n_orders <= 0 or len(cand) == 0:
        return 0
    nx = pd.merge_asof(cand[["cidx", "entry_ts"]].reset_index().sort_values("entry_ts"),
                       o[["cidx", "ts_utc"]].sort_values("ts_utc"), left_on="entry_ts", right_on="ts_utc", by="cidx",
                       direction="forward", allow_exact_matches=False).set_index("index").reindex(cand.index)
    cand = cand[nx.ts_utc.isna() | (nx.ts_utc > cand.entry_ts + pd.Timedelta(days=window))]
    # one incremental order at most per entry (customer, entry_ts)
    cand = cand.sample(frac=1, random_state=int(rng.integers(1e9))).drop_duplicates(["cidx", "entry_ts"])
    pick = cand.head(int(n_orders))
    click_ts = pick.send_ts + pd.to_timedelta(rng.exponential(4 * 3600, len(pick)), unit="s")
    ots = click_ts + pd.to_timedelta(rng.uniform(0.02, extra_click_window, len(pick)) * 86400, unit="s")
    prod = np.where(rng.random(len(pick)) < 0.7, PI["P01"], PI["P02"])
    disc = np.where(pick.message.str.contains("comeback"), 0.10, 0.0)
    ids = book.add(pick.cidx.to_numpy(), ots.values, prod, np.ones(len(pick), int), "oneoff", disc, source=f"incremental:{flow}")
    ev.loc[pick.index, ["opened", "clicked"]] = True
    ev.loc[pick.index, "open_ts"] = (click_ts - pd.Timedelta(minutes=3)).values
    ev.loc[pick.index, "click_ts"] = click_ts.values
    ev.loc[pick.index, "mpp_flag"] = False
    return len(ids)


def main():
    SIM.mkdir(parents=True, exist_ok=True)
    cust, book, st = generate()
    z = st["z"]
    subs = pd.concat(st["subs"], ignore_index=True)
    o = orders_frame(book)
    print(f"base: {len(cust):,} customers, {len(o):,} orders, {len(subs):,} subscriptions")
    apple = rng.random(len(cust)) < 0.33
    # loyalty tiers from points (1 point per euro paid after joining)
    o["paid"] = o.gross_eur - o.discount_eur
    ms = st["member_since"]
    oc = o.sort_values("ts_utc").assign(cum=lambda d: d.groupby("cidx").paid.cumsum())
    cross = oc[oc.cum >= 300].drop_duplicates("cidx").set_index("cidx").ts_utc
    cross = cross[ms[cross.index] < np.datetime64("2100-01-01")]
    gold = pd.Series(np.maximum(cross.values, ms[cross.index]), index=cross.index)
    gold_since = np.full(len(cust), np.datetime64("2100-01-01"), "datetime64[ns]")
    gold_since[gold.index.to_numpy()] = gold.values
    # flow entries
    ent = [entries_welcome(cust), entries_education(cust, o), entries_replenishment(cust, o, subs),
           entries_from_subs(subs, "F5_sub_onboarding")]
    t3 = o.sort_values("ts_utc").drop_duplicates("cidx")
    t3 = t3[t3["prod"].isin([PI["P05"], PI["P06"], PI["P09"]]) & ~t3.is_subscription & cust.consent_email.to_numpy()[t3.cidx]]
    ent.append(pd.DataFrame({"cidx": t3.cidx, "entry_ts": t3.ts_utc, "flow": "F3_trial_to_sub", "variant": "standard"}))
    ce = pd.concat(st["cancel_events"], ignore_index=True)
    ce = ce[cust.consent_email.to_numpy()[ce.cidx]]
    ent.append(pd.DataFrame({"cidx": ce.cidx, "entry_ts": pd.to_datetime(ce.ts) - pd.Timedelta(hours=1), "flow": "F6_cancel_save",
                             "variant": "standard"}))
    ent.append(entries_winback(cust, o, subs))
    gl = gold[cust.consent_email.to_numpy()[gold.index]]
    ent.append(pd.DataFrame({"cidx": gl.index, "entry_ts": gl.values, "flow": "F8_vip_loyalty", "variant": "standard"}))
    entries = pd.concat(ent, ignore_index=True)
    entries = entries[entries.entry_ts <= END]
    sends = build_sends(entries, o)
    camp = campaign_recipients(cust, o, ms, gold_since)
    camp["entry_ts"] = camp.send_ts
    allsends = pd.concat([sends, camp.drop(columns=["kind", "disc"])], ignore_index=True)
    open_base = pd.Series({"F1_welcome": 0.1, "F2_education": -0.35, "F3_trial_to_sub": -0.2, "F4_replenishment": -0.3,
                           "F5_sub_onboarding": 0.2, "F6_cancel_save": 0.4, "F7_winback": -1.1, "F8_vip_loyalty": 0.3})
    base_click = pd.Series({"F1_welcome": 0.05, "F2_education": 0.035, "F3_trial_to_sub": 0.04,
                            "F4_replenishment": 0.03, "F5_sub_onboarding": 0.05, "F6_cancel_save": 0.12, "F7_winback": 0.015,
                            "F8_vip_loyalty": 0.06})
    q_tied = pd.Series({"F2_education": 0.38, "F4_replenishment": 0.22, "F1_welcome": 0.2, "F7_winback": 0.12})
    erng = np.random.default_rng(7)
    ev = engagement(allsends, o, z, apple, q_tied, base_click, open_base, erng)
    ev["send_id"] = np.arange(1, len(ev) + 1)
    # ---- calibration of the incremental orders (events 1 and 2), then campaign and test effects
    att = attribute(o, ev).merge(ev[["send_id", "variant"]], on="send_id", how="left")
    a_edu = att[att.flow_or_campaign == "F2_education"].attributed_revenue_eur.sum()
    aov = PRICE[[PI["P01"], PI["P02"]]] @ [0.7, 0.3]
    n_edu = 0.22 / 0.78 * a_edu / aov
    add_incremental(book, o, ev, "F2_education", round(n_edu), extra_click_window=4, window=45)
    a_rep = att[att.flow_or_campaign == "F4_replenishment"]
    rep_t = ev[(ev.flow == "F4_replenishment") & ~ev.holdout_flag].drop_duplicates(["cidx", "entry_ts"])
    n21 = (rep_t.variant == "J21").sum()
    n26 = (rep_t.variant == "J26_branch").sum()
    need = 0.61 / 0.39 * a_rep.attributed_revenue_eur.sum() / aov
    u21 = max((need - 0.041 * n26) / (n21 + n26), 0.004)
    add_incremental(book, o, ev, "F4_replenishment", round(u21 * n21), variant="J21", extra_click_window=4)
    add_incremental(book, o, ev, "F4_replenishment", round((u21 + 0.041) * n26), variant="J26_branch", extra_click_window=4)
    fr_ad = ev[(ev.flow == "F1_welcome") & (ev.variant == "FR_adapted")].cidx.nunique()
    add_incremental(book, o, ev, "F1_welcome", round(0.9 / aov * fr_ad), variant="FR_adapted", extra_click_window=6, window=14)
    for f in ev.flow[ev.flow.str.contains("early access (Gold)", regex=False)].unique():
        n_vip = ev[(ev.flow == f) & ev.sent].shape[0]
        add_incremental(book, o, ev, f, round(0.03 * n_vip), extra_click_window=1.5, window=7)
    # campaigns with a discount code: clickers who buy (no holdout: their lift is not measured here)
    for i, (d, name, kind, disc, seg) in enumerate(CAMPAIGNS):
        f = f"CMP{i + 1:02d} {name}"
        clk = ev[(ev.flow == f) & ev.clicked]
        buy = clk[rng.random(len(clk)) < (0.10 if disc > 0 else 0.03)]
        ots = buy.click_ts + pd.to_timedelta(rng.uniform(0.01, 1.5, len(buy)) * 86400, unit="s")
        prod = rng.choice([PI["P01"], PI["P02"], PI["P10"], PI["P11"], PI["P03"]], len(buy), p=[.4, .2, .15, .15, .1])
        if "Energy" in name:
            prod[:] = PI["P08"]
        book.add(buy.cidx.to_numpy(), ots.values, prod, np.ones(len(buy), int), "oneoff", np.full(len(buy), disc),
                 campaign=f, source="campaign")
    # subject-line test: variant B loses on purchases even though it wins on opens
    o = orders_frame(book)
    att = attribute(o, ev)
    write_tables(cust, o, book, subs, st, ev, att, apple, gold_since, ms)


def write_tables(cust, o, book, subs, st, ev, att, apple, gold_since, ms):
    cid = cust.customer_id.to_numpy()
    o = o.reset_index(drop=True)
    o["order_id"] = [f"O{x:07d}" for x in o.order_no]
    paid = o.gross_eur - o.discount_eur
    o["shipping_eur"] = np.round(SHIP_A[st["mk"][o.cidx]] + np.where(o.qty >= 3, 4.00, 0.0), 2)   # 3 jars: heavier parcel
    o["payment_fee_eur"] = np.round(paid * 0.019 + 0.25, 2)
    ref = rng.random(len(o)) < np.where(o.is_subscription, 0.01, 0.025)
    o["refund_eur"] = np.where(ref, np.round(paid, 2), 0.0)
    o["market"] = st["mk"][o.cidx]
    o["market"] = MKTS[o.market]
    o["customer_id"] = cid[o.cidx]
    o["subscription_id"] = np.where(o.sub_id > 0, ["S" + f"{x:06d}" for x in o.sub_id.clip(lower=0)], None)
    # ---- event 8a: 2,300 DE customers split into a duplicate AT profile (same email hash) for their later orders
    de_multi = o[o.market == "DE"].groupby("cidx").size()
    de_multi = de_multi[de_multi >= 2].index.to_numpy()
    dup_src = rng.choice(de_multi, 2300, replace=False)
    n0 = len(cust)
    dup = cust.set_index("cidx").loc[dup_src].reset_index()
    dup["new_cidx"] = np.arange(n0, n0 + len(dup))
    first_ts = o.groupby("cidx").ts_utc.min()
    move = o.cidx.isin(dup_src) & (o.ts_utc > o.cidx.map(first_ts))
    mapping = dict(zip(dup.cidx, dup.new_cidx))
    newid = {c: f"C{c + 1:06d}" for c in dup.new_cidx}
    o.loc[move, "customer_id"] = o.loc[move, "cidx"].map(mapping).map(newid)
    o.loc[move, "market"] = "AT"
    dup_rows = pd.DataFrame({"customer_id": list(newid.values()), "market": "AT",
                             "first_order_ts": o[move].groupby(o.loc[move, "cidx"]).ts_utc.min().reindex(dup.cidx).values,
                             "acquisition_channel": dup.acquisition_channel.values, "consent_email": dup.consent_email.values,
                             "consent_sms": dup.consent_sms.values, "email_hash": dup.email_hash.values})
    # customers table
    member = ms < np.datetime64("2100-01-01")
    tier = np.where(gold_since < np.datetime64("2100-01-01"), "gold", np.where(member, "member", None))
    cust_out = cust.drop(columns="cidx").assign(loyalty_member=member, loyalty_tier=tier,
                                                loyalty_joined_ts=pd.Series(ms).where(member).values)
    dup_rows = dup_rows.assign(loyalty_member=False, loyalty_tier=None, loyalty_joined_ts=pd.NaT)
    customers = pd.concat([cust_out, dup_rows], ignore_index=True)
    customers["first_order_date"] = customers.first_order_ts.dt.date
    customers[["customer_id", "market", "first_order_date", "first_order_ts", "acquisition_channel", "consent_email", "consent_sms",
               "loyalty_member", "loyalty_tier", "loyalty_joined_ts", "email_hash"]].to_parquet(SIM / "customers.parquet", index=False)
    orders = o[["order_id", "customer_id", "ts_utc", "market", "is_subscription", "subscription_id", "gross_eur", "discount_eur",
                "shipping_eur", "cogs_eur", "payment_fee_eur", "refund_eur"]].assign(campaign_code=o.campaign)
    orders.to_parquet(SIM / "orders.parquet", index=False)
    lines = pd.concat(book.lines, ignore_index=True).merge(o[["order_no", "order_id"]], on="order_no")
    lines["line_no"] = lines.groupby("order_id").cumcount() + 1
    lines[["order_id", "line_no", "product_id", "qty", "unit_price_eur", "line_gross_eur"]].to_parquet(SIM / "order_lines.parquet", index=False)
    s = subs.copy()
    s["subscription_id"] = ["S" + f"{x:06d}" for x in s.subscription_id]
    s["customer_id"] = cid[s.cidx]
    s[["subscription_id", "customer_id", "product", "interval", "discount", "created", "cancelled", "cancel_reason", "skips", "swaps",
       "origin"]].to_parquet(SIM / "subscriptions.parquet", index=False)
    ch = pd.concat(st["charges"], ignore_index=True)
    ch["subscription_id"] = ["S" + f"{x:06d}" for x in ch.subscription_id]
    ch["charge_id"] = [f"CH{x:07d}" for x in range(1, len(ch) + 1)]
    ch["scheduled_date"] = pd.to_datetime(ch.scheduled_date).dt.date
    ch[["charge_id", "subscription_id", "charge_no", "scheduled_date", "status"]].to_parquet(SIM / "charges.parquet", index=False)
    # email events (customer ids of duplicates are not remapped: the ESP profile is the original one)
    e = ev.copy()
    e["customer_id"] = cid[e.cidx]
    e["market"] = MKTS[st["mk"][e.cidx]]
    e = e.rename(columns={"flow": "flow_or_campaign", "send_ts": "sent_ts"})
    e[["send_id", "customer_id", "flow_or_campaign", "message", "variant", "market", "entry_ts", "sent_ts", "sent", "delivered",
       "opened", "open_ts", "clicked", "click_ts", "bounced", "unsubscribed", "mpp_flag", "holdout_flag"]].to_parquet(
        SIM / "email_events.parquet", index=False)
    att = att.merge(o[["order_no", "order_id"]], on="order_no")
    att[["order_id", "flow_or_campaign", "send_id", "touch", "attributed_revenue_eur"]].to_parquet(SIM / "attributed_orders.parquet", index=False)
    flows = pd.DataFrame([
        ("F1_welcome", "Welcome", "Placed first order (list join at checkout)", "consent_email; not in another welcome in 30 d", "0 h, 2 d, 5 d", "FR: translated vs adapted (A/B, Mar-Aug 2025)", "smart sending 16 h; exit on unsubscribe"),
        ("F2_education", "Post-purchase education", "First order, one-off", "not an active subscriber", "3, 10, 17, 24, 31 d", "by first product (powder / sticks / trial)", "no promo within 3 d of an order"),
        ("F3_trial_to_sub", "Trial pack -> subscription", "First order contains a 225 g trial pack", "not subscribed", "4, 9, 13 d", "opened T2? -> reminder", "exit on any order or subscription"),
        ("F4_replenishment", "Replenishment", "One-off order of a 30-day product", "no order since trigger; not subscribed", "J21 (until May 2026) -> J26 + J33 branch", "'still have product?' -> J33 reminder", "exit on order; skip if a campaign was sent within 1 d"),
        ("F5_sub_onboarding", "Subscription onboarding", "Subscription created", "-", "0 h, 5 d, 20 d", "monthly vs quarterly copy", "no promo emails during onboarding"),
        ("F6_cancel_save", "Cancel-save", "Cancel intent in the customer portal", "active subscriber", "immediate", "reason: too expensive -> swap / too much -> skip", "never for payment failures"),
        ("F7_winback", "Win-back", "90 days without order (launched 2026-01-02)", "no active subscription", "0, 10, 25 d", "past subscriber vs one-off", "exit on order; max 1 entry per 180 d"),
        ("F8_vip_loyalty", "VIP / loyalty", "Reached Gold tier (400 points)", "loyalty member", "0 d; launches -2 d", "-", "VIP early access never discounted"),
    ], columns=["flow_id", "name", "trigger", "filters", "delays", "branches", "suppression"])
    flows.to_parquet(SIM / "flows.parquet", index=False)
    pd.DataFrame([(f"CMP{i + 1:02d}", n, d, k, dd, seg) for i, (d, n, k, dd, seg) in enumerate(CAMPAIGNS)],
                 columns=["campaign_id", "name", "send_date", "type", "discount_rate", "segment"]).to_parquet(SIM / "campaigns.parquet", index=False)
    # loyalty events
    om = o[o.ts_utc.values >= ms[o.cidx]].copy()
    le = pd.concat([pd.DataFrame({"customer_id": cid[member], "ts_utc": ms[member], "event": "joined", "points": 0}),
                    pd.DataFrame({"customer_id": om.customer_id, "ts_utc": om.ts_utc, "event": "points_earned",
                                  "points": np.floor(om.gross_eur - om.discount_eur).astype(int)}),
                    pd.DataFrame({"customer_id": cid[gold_since < np.datetime64("2100-01-01")],
                                  "ts_utc": gold_since[gold_since < np.datetime64("2100-01-01")], "event": "tier_gold", "points": 0})],
                   ignore_index=True)
    le.to_parquet(SIM / "loyalty_events.parquet", index=False)
    pd.read_csv(PUB / "ecb_eur_gbp_monthly.csv").to_parquet(SIM / "fx.parquet", index=False)
    PRODUCTS.to_parquet(SIM / "products.parquet", index=False)
    wb = st["winback30"]
    pd.DataFrame({"customer_id": cid[wb.cidx], "offer_ts": wb.offer_ts, "holdout_flag": wb.holdout_flag}).to_parquet(
        SIM / "winback_offers.parquet", index=False)
    truth = pd.DataFrame([
        (1, "attributed vs incremental", "F2_education incremental share of attributed revenue", 0.22),
        (1, "attributed vs incremental", "F4_replenishment incremental share of attributed revenue", 0.61),
        (2, "replenishment timing", "60-day repurchase J26+branch minus J21 (pts)", 4.1),
        (3, "January false signal", "win-back true incremental effect (pts)", 0.0),
        (3, "January false signal", "reactivation hazard January / December (target: lapsed reorder rate +38 %)", JAN_DEC),
        (4, "monthly vs quarterly", "12-month retention monthly / quarterly", "0.41 / 0.58"),
        (4, "monthly vs quarterly", "quarterly CM-CLV 12m vs monthly (target; via -25 %, heavier parcel, 17 % skips, fewer add-ons)", -0.09),
        (5, "price increase", "too_expensive cancel hazard multiplier FR, IT after 2026-04-01 (other markets x1.1)", 2.4),
        (5, "-30% win-back", "return rate offer / holdout; returners on -30 % churn x2", "0.18 / 0.14"),
        (6, "loyalty self-selection", "membership multiplies the chain reorder probability (target: about +7 % on 180-day reorder)", 1.05),
        (7, "MPP", "machine opens recorded from", "2025-09-01"),
        (7, "MPP", "subject B: open x1.16, click x0.86", "B loses on clicks"),
        (8, "data issues", "duplicate DE->AT profiles", 2300),
        (8, "data issues", "subscription charges processed 00:05-00:59 Berlin (UTC previous evening)", "month slip on the 1st"),
        (0, "FR localisation", "adapted welcome RPR uplift EUR / unsubscribe ratio (Mar 2025 - Feb 2026)", "0.9 / 0.8"),
        (0, "VIP early access", "Gold early-access purchase uplift (pts)", 3.0),
    ], columns=["event_id", "event", "parameter", "planted_value"])
    truth.to_csv(ROOT / "data" / "_hidden_truth.csv", index=False)
    print(f"written: {len(customers):,} profiles, {len(orders):,} orders, {len(s):,} subscriptions, {len(ch):,} charges, "
          f"{len(e):,} email events, {len(att):,} attributed orders")


if __name__ == "__main__":
    main()
