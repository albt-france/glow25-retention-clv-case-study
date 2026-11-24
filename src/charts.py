"""Matplotlib charts for the PDF report (PNG files in a build folder that is not published).
Style: white cards on a grey-beige page, blue for the data, grey for comparison, red for alerts, Segoe UI.
Each chart title ends with its tag: PUBLIC DATA or SIMULATED.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC, PUB = ROOT / "data" / "processed", ROOT / "data" / "public"
IMG = ROOT / "data" / "raw" / "report" / "img"
BLUE, GREY, RED, GREEN, INK, MUTED, GRID = "#2A78D6", "#A3A19A", "#D03B3B", "#2E8B57", "#0B0B0B", "#52514E", "#E1E0D9"
plt.rcParams.update({
    "font.family": "Segoe UI", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.facecolor": "white", "axes.facecolor": "white",
    "legend.frameon": False, "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left"})
PCT = mtick.PercentFormatter(1.0)


def csv(n, folder=PROC):
    return pd.read_csv(folder / f"{n}.csv")


def save(fig, name):
    IMG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(IMG / f"{name}.png", dpi=200)
    plt.close(fig)
    return (IMG / f"{name}.png").as_uri()


def tag(ax, t):
    ax.text(1.0, 1.02, t, transform=ax.transAxes, ha="right", va="bottom", fontsize=8, fontweight="bold",
            color="#1C5CAB" if t.startswith("PUBLIC") else "#9A3B12")


def offer():
    cat = csv("glow25_catalogue", PUB)
    s = cat[cat.subscribable].copy()
    s["short"] = s.handle.str.replace("glow-25-", "").str.replace("glow25-", "").str.replace("kollagen-", "").str.replace("-mit-vitamin-c", "").str[:22]
    s = s.sort_values("price_eur")
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    y = range(len(s))
    ax.barh([i + 0.27 for i in y], s.price_eur, 0.26, color=GREY, label="one-off price")
    ax.barh(y, s.price_eur * 0.85, 0.26, color=BLUE, label="monthly -15 %")
    ax.barh([i - 0.27 for i in y], s.price_eur * 0.75, 0.26, color="#86B6EF", label="every 3 months -25 %")
    ax.set_yticks(list(y), s.short)
    ax.set_xlabel("EUR per unit")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("8 subscribable products, two plans")
    tag(ax, "PUBLIC DATA")
    return save(fig, "offer")


def eurostat():
    e = csv("eurostat_isoc_ec_ibgs", PUB)
    f = e[e.ind_type == "F_Y25_54"].pivot_table(index="geo", columns="indic_is", values="value").sort_values("I_BCBW")
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    y = range(len(f))
    ax.barh([i + 0.2 for i in y], f.I_BCBW, 0.4, color=GREY, label="cosmetics, beauty, wellness")
    ax.barh([i - 0.2 for i in y], f.I_BMED1, 0.4, color=BLUE, label="medicines or supplements")
    for i, (g, r) in enumerate(f.iterrows()):
        ax.text(r.I_BMED1 + 0.5, i - 0.2, f"{r.I_BMED1:.1f}", va="center", fontsize=8, color=RED if g == "FR" else MUTED)
    ax.set_yticks(list(y), f.index)
    ax.set_xlabel("% of women 25-54 who bought online, last 3 months (2024)")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("France: beauty yes, supplements online no")
    tag(ax, "PUBLIC DATA")
    return save(fig, "eurostat")


def wiki():
    w = csv("wikipedia_collagen_pageviews", PUB)
    w["m"] = w.month.astype(str).str[4:6].astype(int)
    w["idx"] = w.views / w.groupby("project").views.transform("mean")
    g = w.groupby(["m", "project"]).idx.mean().unstack()
    fig, ax = plt.subplots(figsize=(6.2, 3.3))
    for p in g.columns:
        ax.plot(g.index, g[p], color=GREY, lw=1, alpha=0.8)
    ax.plot(g.index, g.mean(axis=1), color=BLUE, lw=2.5, label="average of 5 languages")
    ax.axhline(1, color=MUTED, ls="--", lw=0.8)
    ax.set_xticks(range(1, 13), list("JFMAMJJASOND"))
    ax.set_ylabel("views / yearly average")
    ax.legend(fontsize=8)
    ax.set_title("Interest in collagen peaks in January (DE FR IT NL ES)")
    tag(ax, "PUBLIC DATA")
    return save(fig, "wiki")


def cmclv_segments():
    s = csv("cohort_cmclv_by_segment")
    s = s[s.dimension == "first order type"].sort_values("cm_clv_12m")
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.barh(s.segment, s.cm_clv_12m, color=[BLUE if x == "subscription" else GREY for x in s.segment])
    for i, v in enumerate(s.cm_clv_12m):
        ax.text(v + 2, i, f"EUR {v:.0f}", va="center", fontsize=9)
    ax.set_xlabel("contribution margin per customer, first 12 months")
    ax.set_title("12-month CM-CLV by first order")
    tag(ax, "SIMULATED")
    return save(fig, "cmclv")


def repurchase():
    rs, ru = csv("kpi_repurchase"), csv("uci_repurchase")
    rs = rs[rs.segment == "all"]
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.plot(rs.n_days, rs.repurchase_rate, "o-", color=RED, label="Brand G (SIMULATED)")
    ax.plot(ru.n_days, ru.repurchase_rate, "o-", color=BLUE, label="UCI UK online retailer (PUBLIC DATA)")
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xlabel("days after the first order")
    ax.set_ylabel("2nd order within N days")
    ax.legend(fontsize=8)
    ax.set_title("Same SQL, simulated brand and real transactions")
    tag(ax, "SIMULATED + PUBLIC DATA")
    return save(fig, "repurchase")


def sub_curves():
    c = csv("sub_retention_curve")
    sp = csv("sub_plan_economics").set_index("interval")
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    for k, col, lab in (("1M", BLUE, "monthly -15 %"), ("3M", GREY, "every 3 months -25 %")):
        g = c[c.interval == k]
        ax.plot(g.day, g.still_active, "o-", color=col, ms=3,
                label=f"{lab}: retention {sp.loc[k, 'retention_12m']:.0%}, CM-CLV EUR {sp.loc[k, 'cm_clv_12m_eur']:.0f}")
    ax.yaxis.set_major_formatter(PCT)
    ax.set_xlabel("days since the subscription started")
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title("More stay on 3-monthly; more margin on monthly")
    tag(ax, "SIMULATED")
    return save(fig, "subcurves")


def lift():
    fr = csv("flow_holdout_readout")
    fr = fr[fr.attributed_revenue_eur.fillna(0) > 1000].sort_values("attributed_revenue_eur", ascending=False)
    names = (fr.flow.str.replace("F\\d_", "", regex=True).str.replace("_", " ")
             .replace({"VIP early access (Gold)": "VIP early\naccess", "trial to sub": "trial to\nsub", "cancel save": "cancel\nsave"}))
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    x = range(len(fr))
    ax.bar([i - 0.2 for i in x], fr.attributed_revenue_eur / 1000, 0.4, color=GREY, label="attributed (last touch)")
    ax.bar([i + 0.2 for i in x], fr.incremental_revenue_eur / 1000, 0.4, color=BLUE, yerr=fr.incremental_revenue_ci95 / 1000,
           ecolor=INK, capsize=3, label="incremental vs 10 % holdout (95 % CI)")
    ax.set_xticks(list(x), names, fontsize=8)
    ax.set_ylabel("EUR thousand")
    ax.legend(fontsize=8)
    ax.set_title("Attributed vs incremental revenue per flow")
    tag(ax, "SIMULATED")
    return save(fig, "lift")


def gaps():
    g = csv("reorder_gap_distribution")
    g = g[g.gap_days <= 90]
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.bar(g.gap_days, g.reorders, color=BLUE, width=0.9)
    ax.axvline(21, color=RED, ls="--")
    ax.axvline(26, color=GREEN, ls="--")
    top = g.reorders.max()
    ax.text(20.5, top * 0.95, "day 21", color=RED, ha="right", fontsize=9)
    ax.text(26.5, top * 0.95, "day 26", color=GREEN, fontsize=9)
    ax.set_xlabel("days between two one-off orders of a 30-day jar")
    ax.set_ylabel("reorders")
    ax.set_title("Reorders cluster around day 32-34")
    tag(ax, "SIMULATED")
    return save(fig, "gaps")


def j26():
    r = csv("replenishment_j21_vs_j26")
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    labs = ["day 21", "day 26 + branch", "holdout"]
    ax.bar(labs, r.repurchase_60d, color=[BLUE, GREEN, GREY], yerr=r.repurchase_ci95, capsize=4, ecolor=INK)
    for i, v in enumerate(r.repurchase_60d):
        ax.text(i, 0.415, f"{v:.1%}", ha="center", color="white", fontweight="bold")
    ax.set_ylim(0.4, 0.6)
    ax.yaxis.set_major_formatter(PCT)
    ax.set_ylabel("60-day repurchase")
    ax.set_title("A/B (Feb-May 2026 triggers): day 26 wins")
    tag(ax, "SIMULATED")
    return save(fig, "j26")


def january():
    lap = csv("lapsed_reactivation_by_month")
    w = csv("winback_january_readout")
    j0 = w[w.entry_month.str.startswith("2026-01")].iloc[0]
    lap["month"] = pd.to_datetime(lap.month)
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    ax.plot(lap.month, lap.reorder_rate, "o-", color=GREY, label="lapsed customers reordering in the month")
    ax.axvline(pd.Timestamp("2026-01-02"), color=INK, ls=":", lw=1)
    ax.text(pd.Timestamp("2026-01-06"), lap.reorder_rate.max() * 1.02, "win-back launched", fontsize=8)
    ax.bar([pd.Timestamp("2026-01-10")], [j0.conv_treated], width=6, color=BLUE, label=f"Jan entrants, flow: {j0.conv_treated:.1%}")
    ax.bar([pd.Timestamp("2026-01-18")], [j0.conv_holdout], width=6, color=RED, label=f"Jan entrants, holdout: {j0.conv_holdout:.1%}")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0, decimals=1))
    ax.set_ylim(0, lap.reorder_rate.max() * 1.25)
    ax.legend(fontsize=7.5, loc="lower left")
    ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 3, 5, 9, 11]))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y"))
    ax.set_title("January rises with or without the flow")
    tag(ax, "SIMULATED")
    return save(fig, "january")


def price_increase():
    p = csv("price_increase_too_expensive")
    piv = p.pivot(index="market", columns="period", values="per_1000_active")
    cols = sorted(piv.columns, key=lambda c: 0 if c.startswith("Oct") else 1)
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    x = range(len(piv))
    ax.bar([i - 0.2 for i in x], piv[cols[0]], 0.4, color=GREY, label="Oct 2025 - Mar 2026")
    ax.bar([i + 0.2 for i in x], piv[cols[1]], 0.4, color=RED, label="Apr - Sep 2026 (after +10 %)")
    ax.set_xticks(list(x), piv.index)
    ax.set_ylabel("per 1,000 active subs / month")
    ax.legend(fontsize=8)
    ax.set_title("'Too expensive' cancellations after the price rise")
    tag(ax, "SIMULATED")
    return save(fig, "price")


def loyalty_mpp():
    loy = csv("loyalty_naive_vs_matched")
    en = csv("email_monthly_engagement")
    en["month"] = pd.to_datetime(en.month)
    en = en[(en.month >= "2024-11-01") & (en.month <= "2026-09-01")]       # full months only
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.4, 4.4), gridspec_kw={"width_ratios": [1, 1.6]})
    a1.bar(["naive", "matched"], loy.relative_lift, color=[GREY, BLUE])
    for i, v in enumerate(loy.relative_lift):
        a1.text(i, v + 0.01, f"{v:+.0%}", ha="center", fontsize=9)
    a1.yaxis.set_major_formatter(PCT)
    a1.set_title("Loyalty lift", fontsize=10)
    a2.plot(en.month, en.open_rate, color=RED, label="open rate")
    a2.plot(en.month, en.open_rate_excl_machine, color=GREY, label="without machine opens")
    a2.plot(en.month, en.click_rate * 10, color=BLUE, label="click rate x10")
    a2.yaxis.set_major_formatter(PCT)
    a2.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[1, 7]))
    a2.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %y"))
    a2.tick_params(axis="x", labelsize=7)
    a2.legend(fontsize=7)
    a2.set_title("Opens jump in Sep 2025, clicks do not", fontsize=10)
    tag(a2, "SIMULATED")
    return save(fig, "loyalty_mpp")


def saves():
    cs = csv("cancel_save_readout").set_index("arm")
    wb = csv("winback30_readout").set_index("arm")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.4, 4.4))
    v1 = [cs.loc["holdout (plain cancel page)", "save_rate"], cs.loc["skip / swap / pause offered", "save_rate"]]
    a1.bar(["plain cancel", "skip / swap /\npause offered"], v1, color=[GREY, BLUE],
           yerr=[cs.loc["holdout (plain cancel page)", "save_rate_ci95"], cs.loc["skip / swap / pause offered", "save_rate_ci95"]], capsize=4)
    for i, v in enumerate(v1):
        a1.text(i, v / 2, f"{v:.0%}", ha="center", color="white", fontweight="bold")
    a1.yaxis.set_major_formatter(PCT)
    a1.set_title("Save rate on cancel intents", fontsize=10)
    v2 = [wb.loc["holdout (no offer)", "cm_per_recipient_180d"], wb.loc["-30 % offer", "cm_per_recipient_180d"]]
    a2.bar(["no offer\n(holdout)", "-30 % offer"], v2, color=[GREY, RED],
           yerr=[wb.loc["holdout (no offer)", "cm_ci95"], wb.loc["-30 % offer", "cm_ci95"]], capsize=4)
    for i, (v, r) in enumerate(zip(v2, [wb.loc["holdout (no offer)", "return_rate"], wb.loc["-30 % offer", "return_rate"]])):
        a2.text(i, 0.6, f"EUR {v:.2f}\n{r:.0%} back", ha="center", color="white", fontweight="bold", fontsize=8.5)
    a2.set_ylabel("CM per recipient, 180 days (EUR)")
    a2.set_title("-30 % comeback offer", fontsize=10)
    tag(a2, "SIMULATED")
    return save(fig, "saves")


def build_all():
    return {n: f() for n, f in (("offer", offer), ("eurostat", eurostat), ("wiki", wiki), ("cmclv", cmclv_segments),
                                ("repurchase", repurchase), ("subcurves", sub_curves), ("lift", lift), ("gaps", gaps), ("j26", j26),
                                ("january", january), ("price", price_increase), ("loyalty_mpp", loyalty_mpp), ("saves", saves))}


if __name__ == "__main__":
    print(list(build_all()))
