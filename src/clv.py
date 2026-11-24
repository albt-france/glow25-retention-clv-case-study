"""Customer value, two ways, and a check of both on real transactions.

1. Empirical CLV ("chain ladder"): cumulative value per customer by cohort and month since first order; young
   cohorts are projected with the average month-to-month growth of older cohorts. Transparent, no model.
2. BG/NBD (purchase frequency and drop-out) + Gamma-Gamma (spend per purchase), the standard "buy till you die"
   models. The `lifetimes` package does not import with pandas 2.3, so both likelihoods are written here with
   scipy (Fader, Hardie & Lee 2005; Fader & Hardie 2013).

Back-test on PUBLIC DATA (UCI Online Retail II, UK retailer, 2009-2011): fit on purchases up to 30 June 2011,
predict July - November 2011, compare with what really happened. Then the empirical method is applied to the
SIMULATED Brand G cohorts (contribution margin, not revenue).

    python src/clv.py   -> data/processed/clv_*.csv
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy import optimize, special

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
CAL_END, HOLD_END = pd.Timestamp("2011-07-01"), pd.Timestamp("2011-12-01")


# ------------------------------------------------------------------ BG/NBD and Gamma-Gamma
def bgnbd_ll(params, x, tx, T):
    r, alpha, a, b = np.exp(params)
    a1 = special.gammaln(r + x) - special.gammaln(r) + r * np.log(alpha)
    a2 = special.gammaln(a + b) + special.gammaln(b + x) - special.gammaln(b) - special.gammaln(a + b + x)
    a3 = -(r + x) * np.log(alpha + T)
    a4 = np.where(x > 0, np.log(a) - np.log(np.maximum(b + x - 1, 1e-9)) - (r + x) * np.log(alpha + tx), -np.inf)
    return -np.sum(a1 + a2 + np.logaddexp(a3, a4))


def bgnbd_fit(x, tx, T):
    res = optimize.minimize(bgnbd_ll, np.log([0.5, 5.0, 0.5, 2.0]), args=(x, tx, T), method="Nelder-Mead",
                            options={"maxiter": 4000, "xatol": 1e-6, "fatol": 1e-6})
    return np.exp(res.x)


def bgnbd_expected(t, x, tx, T, r, alpha, a, b):
    """Expected number of purchases in the next t periods for a customer with history (x, tx, T)."""
    z = t / (alpha + T + t)
    hyp = special.hyp2f1(r + x, b + x, a + b + x - 1, z)
    num = (a + b + x - 1) / (a - 1) * (1 - ((alpha + T) / (alpha + T + t)) ** (r + x) * hyp)
    den = 1 + (x > 0) * a / np.maximum(b + x - 1, 1e-9) * ((alpha + T) / (alpha + tx)) ** (r + x)
    return num / den


def gg_ll(params, x, m):
    p, q, v = np.exp(params)
    return -np.sum(special.gammaln(p * x + q) - special.gammaln(p * x) - special.gammaln(q) + q * np.log(v)
                   + (p * x - 1) * np.log(m) + p * x * np.log(x) - (p * x + q) * np.log(x * m + v))


def gg_fit(x, m):
    res = optimize.minimize(gg_ll, np.log([2.0, 3.0, 10.0]), args=(x, m), method="Nelder-Mead", options={"maxiter": 4000})
    return np.exp(res.x)


# ------------------------------------------------------------------ empirical chain ladder
def chain_ladder(cum: pd.DataFrame, horizon: int, min_cohorts: int = 3) -> pd.DataFrame:
    """cum: cohort x month_index cumulative value per customer (NaN where not observed yet)."""
    proj = cum.copy()
    for k in range(1, horizon):
        if k not in proj.columns:
            proj[k] = np.nan
        both = cum[[k - 1, k]].dropna() if k in cum.columns else pd.DataFrame()
        f = (both[k].sum() / both[k - 1].sum()) if len(both) >= min_cohorts else np.nan
        if np.isnan(f):                                      # not enough history: carry the last factor
            f = last_f
        last_f = f
        proj[k] = proj[k].fillna(proj[k - 1] * f)
    return proj[sorted(c for c in proj.columns if c < horizon)]


def uci_backtest(con):
    inv = con.execute(f"select customer_id, invoice_ts, amount_gbp from read_parquet('{(ROOT / 'data/public/uci_invoices.parquet').as_posix()}')").df()
    first = inv.groupby("customer_id").invoice_ts.min()
    cal = inv[inv.invoice_ts < CAL_END]
    hold = inv[(inv.invoice_ts >= CAL_END) & (inv.invoice_ts < HOLD_END)]
    cust = cal.groupby("customer_id").agg(first=("invoice_ts", "min"), last=("invoice_ts", "max"), n=("invoice_ts", "size"),
                                          spend=("amount_gbp", "sum"))
    # one purchase per customer-day (several invoices on the same day = one transaction)
    days = cal.assign(d=cal.invoice_ts.dt.normalize()).groupby(["customer_id", "d"]).amount_gbp.sum().reset_index()
    rep = days.groupby("customer_id").agg(n_days=("d", "size"), first_d=("d", "min"), last_d=("d", "max"), spend=("amount_gbp", "sum"))
    x = (rep.n_days - 1).to_numpy(float)
    tx = ((rep.last_d - rep.first_d).dt.days / 7).to_numpy(float)
    T = ((CAL_END - rep.first_d).dt.days / 7).to_numpy(float)
    r, alpha, a, b = bgnbd_fit(x, tx, T)
    t_hold = (HOLD_END - CAL_END).days / 7
    exp_n = bgnbd_expected(t_hold, x, tx, T, r, alpha, a, b)
    # Gamma-Gamma on repeat customers: average spend per repeat transaction
    rep_days = days.merge(rep[["first_d"]], left_on="customer_id", right_index=True)
    rep_tx = rep_days[rep_days.d > rep_days.first_d].groupby("customer_id").amount_gbp.agg(["mean", "size"])
    rep_tx = rep_tx[rep_tx["mean"] > 0]
    p, q, v = gg_fit(rep_tx["size"].to_numpy(float), rep_tx["mean"].to_numpy(float))
    xm = rep_tx.reindex(rep.index)
    m_bar = np.where(xm["size"].notna(), (p * (v + xm["size"].fillna(0) * xm["mean"].fillna(0)))
                     / (p * xm["size"].fillna(0) + q - 1), p * v / (q - 1))
    pred_bg = float(np.sum(exp_n * m_bar))
    pred_bg_n = float(np.sum(exp_n))
    actual_days = hold[hold.customer_id.isin(rep.index)].assign(d=lambda d: d.invoice_ts.dt.normalize()).groupby(
        ["customer_id", "d"]).amount_gbp.sum()
    actual_rev = float(actual_days.sum())
    actual_n = float(len(actual_days))
    # empirical: chain ladder on monthly cohorts of the calibration period
    cal_m = cal.assign(cohort=cal.customer_id.map(first).dt.to_period("M"), m=cal.invoice_ts.dt.to_period("M"))
    cal_m = cal_m[cal_m.cohort >= pd.Period("2009-12", "M")]
    cal_m["k"] = (cal_m.m - cal_m.cohort).apply(lambda d: d.n)
    size = cal_m.groupby("cohort").customer_id.nunique()
    rev = cal_m.groupby(["cohort", "k"]).amount_gbp.sum().unstack().div(size, axis=0)
    cum = rev.fillna(0).cumsum(axis=1)
    last_k = {c: (pd.Period("2011-06", "M") - c).n for c in cum.index}
    for c in cum.index:
        cum.loc[c, [k for k in cum.columns if k > last_k[c]]] = np.nan
    proj = chain_ladder(cum, horizon=int(max(last_k.values())) + 6)
    pred_emp = 0.0
    for c in proj.index:
        k0 = last_k[c]
        pred_emp += (proj.loc[c, k0 + 5] - proj.loc[c, k0]) * size[c]
    rows = [("BG/NBD + Gamma-Gamma (fitted, scipy)", pred_bg_n, pred_bg),
            ("Empirical chain ladder (cohort averages)", np.nan, pred_emp),
            ("Actual (what happened)", actual_n, actual_rev)]
    bt = pd.DataFrame(rows, columns=["method", "purchases_jul_nov_2011", "revenue_jul_nov_2011_gbp"])
    bt["error_vs_actual"] = bt.revenue_jul_nov_2011_gbp / actual_rev - 1
    bt["customers"] = len(rep)
    bt["data"] = "PUBLIC DATA (UCI Online Retail II, UK online retailer, method demo)"
    params = pd.DataFrame({"parameter": ["r", "alpha", "a", "b", "p", "q", "v"], "value": [r, alpha, a, b, p, q, v]})
    return bt, params


def sim_cmclv(con):
    """Empirical CM-CLV for the SIMULATED Brand G cohorts, projected to 24 months."""
    d = pd.read_csv(OUT / "cohort_retention.csv", parse_dates=["cohort_month"])
    cum = d.pivot(index="cohort_month", columns="month_index", values="cm_clv_eur")
    proj = chain_ladder(cum, horizon=24)
    size = d.groupby("cohort_month").customers.first()
    out = pd.DataFrame({"cohort_month": proj.index.date, "customers": size.values,
                        "observed_months": cum.notna().sum(axis=1).values,
                        "cm_clv_12m_eur": proj[11].values, "cm_clv_24m_eur": proj[23].values,
                        "cm_clv_12m_observed": cum.notna()[11].values if 11 in cum else False})
    out["data"] = "SIMULATED (Brand G)"
    return out


if __name__ == "__main__":
    con = duckdb.connect()
    bt, params = uci_backtest(con)
    bt.to_csv(OUT / "clv_uci_backtest.csv", index=False)
    params.to_csv(OUT / "clv_uci_model_params.csv", index=False)
    sc = sim_cmclv(con)
    sc.to_csv(OUT / "clv_sim_cmclv_projection.csv", index=False)
    print(bt[["method", "revenue_jul_nov_2011_gbp", "error_vs_actual"]].round(3).to_string(index=False))
    print(f"Brand G (SIMULATED) mean CM-CLV 12m {sc.cm_clv_12m_eur.mean():.1f} EUR, 24m {sc.cm_clv_24m_eur.mean():.1f} EUR")
