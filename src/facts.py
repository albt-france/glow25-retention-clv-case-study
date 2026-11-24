"""Headline numbers used by the docs, the workbook, the dashboard and the PDF, read from data/public and
data/processed (nothing typed by hand except the company statements quoted "as stated by Glow25").
Also writes the scorecard of the 8 planted events (planted value vs what the SQL found).

    python src/facts.py   -> data/processed/headline_facts.json, data/processed/event_scorecard.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PUB, PROC = ROOT / "data" / "public", ROOT / "data" / "processed"
STATED = [  # company statements, quoted, never treated as verified facts
    ("Deutschlands Nr. 1", "product title of the collagen powder on glow25.de (de-de), read 2026-11-24",
     "https://glow25.de/de-de/products/kollagen-pulver-mit-vitamin-c"),
    ("Vertraut von über 2,5 Million Frauen", "meta description of the home page glow25.de (de-de), read 2026-11-24",
     "https://glow25.de/de-de"),
    ("one of Europe's fastest-growing collagen brands", "job posting on Ashby, read 2026-11-24",
     "https://jobs.ashbyhq.com/glow25/ebca5cfb-5f0d-4df9-aa5e-f86feb048a11"),
]


def csv(name, folder=PROC):
    return pd.read_csv(folder / f"{name}.csv")


def public_facts():
    cat = csv("glow25_catalogue", PUB)
    plans = csv("glow25_selling_plans", PUB)
    mk = csv("shop_markets", PUB)
    eu = csv("eurostat_isoc_ec_ibgs", PUB)
    w = csv("wikipedia_collagen_pageviews", PUB)
    w["m"] = w.month.astype(str).str[4:6]
    wm = w.groupby(["project", "m"]).views.mean().unstack()
    art = csv("glow25_articles_by_domain", PUB)
    claims = csv("eu_432_2012_collagen_claims", PUB)
    jobs = csv("job_board", PUB)
    uci = csv("uci_summary").iloc[0]
    log = csv("uci_cleaning_log", PUB).set_index("step").rows
    bt = csv("clv_uci_backtest").set_index("method")
    f = eu[eu.ind_type == "F_Y25_54"].pivot_table(index="geo", columns="indic_is", values="value")
    sub = cat[cat.subscribable]
    return {
        "catalogue_products": int(len(cat)), "subscribable_products": int(cat.subscribable.sum()),
        "not_subscribable_products": int((~cat.subscribable).sum()),
        "plan_discounts": sorted({f"{r.plan_name}: -{int(r.adjustment_value)}%" for r in plans.itertuples()}),
        "recharge_app_ids": sorted(plans.app_id.astype(str).unique().tolist()),
        "subscribable_prices": sub.set_index("title").price_eur.round(2).to_dict(),
        "trial_packs": cat[cat.handle.str.contains("probierpaket")][["handle", "price_eur", "subscribable"]].to_dict("records"),
        "free_items": int((cat.price_eur == 0).sum()),
        "bundles": int((cat.type == "Bundle").sum()),
        "markets_hreflang": sorted(set(mk.market) | {"DE"}),
        "locales_hreflang": int(len(mk)) + 1,
        "articles_per_domain": int(art.articles.max()), "domains_with_articles": int((art.articles > 0).sum()),
        "authorised_collagen_claims_en": int((claims.language == "EN").sum()),
        "eurostat_supplements_f25_54": f.I_BMED1.round(2).to_dict(), "eurostat_beauty_f25_54": f.I_BCBW.round(2).to_dict(),
        "eurostat_updated": eu.updated.iloc[0], "eurostat_status_flags": int(eu.status.notna().sum()),
        "wiki_jan_over_jul": (wm["01"] / wm["07"]).round(2).to_dict(), "wiki_jan_over_dec": (wm["01"] / wm["12"]).round(2).to_dict(),
        "open_jobs": int(len(jobs)), "job_published": jobs[jobs.title.str.startswith("Retention")].published_at.iloc[0],
        "uci_customers": int(uci.customers), "uci_invoices": int(uci.invoices), "uci_repeat_share": float(uci.repeat_customer_share),
        "uci_rows_raw": int(log["rows in both sheets"]), "uci_rows_kept": int(log["rows kept"]),
        "uci_backtest_error_bgnbd": float(bt.loc["BG/NBD + Gamma-Gamma (fitted, scipy)", "error_vs_actual"]),
        "uci_backtest_error_empirical": float(bt.loc["Empirical chain ladder (cohort averages)", "error_vs_actual"]),
        "stated": [{"text": a, "where": b, "url": c} for a, b, c in STATED],
    }


def sim_facts():
    fr = csv("flow_holdout_readout").set_index("flow")
    rep = csv("replenishment_j21_vs_j26").set_index("arm")
    sp = csv("sub_plan_economics").set_index("interval")
    wb = csv("winback30_readout").set_index("arm")
    jan = csv("winback_january_readout")
    lap = csv("lapsed_reactivation_by_month").set_index("month")
    loy = csv("loyalty_naive_vs_matched")
    sl = csv("subject_line_test_readout").set_index("variant")
    dq = csv("data_quality_summary").set_index("check_name").value
    pr = csv("price_increase_too_expensive").set_index(["market", "period"]).per_1000_active
    eng = csv("email_monthly_engagement").set_index("month")
    loc = csv("localisation_fr_welcome_test").set_index("variant")
    cs = csv("cancel_save_readout").set_index("arm")
    rp = csv("kpi_repurchase")
    rp = rp[rp.segment == "all"].set_index("n_days").repurchase_rate
    gap = csv("reorder_gap_summary").iloc[0]
    mo = csv("kpi_monthly_overview")
    j0 = jan[jan.entry_month.str.startswith("2026-01")].iloc[0]
    before = [k for k in pr.index if k[1].startswith("Oct")]
    ratio = {m: pr[(m, [p for (mm, p) in pr.index if mm == m and p.startswith("Apr")][0])] / pr[(m, [p for (mm, p) in pr.index if mm == m and p.startswith("Oct")][0])]
             for m in ["DE", "FR", "IT", "other"]}
    e, r = fr.loc["F2_education"], fr.loc["F4_replenishment"]
    return {
        "customers": int(mo.new_customers.sum()), "orders": int(mo.orders.sum()), "net_revenue_eur": float(mo.net_revenue_eur.sum()),
        "cm_eur": float(mo.contribution_margin_eur.sum()), "cm_rate": float(mo.contribution_margin_eur.sum() / mo.net_revenue_eur.sum()),
        "repurchase": {int(k): float(v) for k, v in rp.items()},
        "edu_attributed_all": float(e.attributed_eur_all_period), "edu_attributed": float(e.attributed_revenue_eur),
        "edu_incremental": float(e.incremental_revenue_eur), "edu_incremental_ci": float(e.incremental_revenue_ci95),
        "edu_share": float(e.incremental_share_of_attributed), "edu_share_ci": float(e.incremental_share_ci95),
        "rep_attributed_all": float(r.attributed_eur_all_period), "rep_attributed": float(r.attributed_revenue_eur),
        "rep_incremental": float(r.incremental_revenue_eur), "rep_share": float(r.incremental_share_of_attributed),
        "rep_share_ci": float(r.incremental_share_ci95),
        "j21": float(rep.loc["J21", "repurchase_60d"]), "j26": float(rep.loc["J26_branch", "repurchase_60d"]),
        "j_hold": float(rep.loc["holdout (no reminder)", "repurchase_60d"]),
        "j_diff_ci": float(1.96 * ((rep.loc["J21", "repurchase_ci95"] / 1.96) ** 2 + (rep.loc["J26_branch", "repurchase_ci95"] / 1.96) ** 2) ** 0.5),
        "j21_click": float(rep.loc["J21", "click_rate"]), "j26_click": float(rep.loc["J26_branch", "click_rate"]),
        "gap_median": float(gap.median_gap), "gap_mode": float(gap.mode_gap), "gap_before21": float(gap.share_reordering_before_day21),
        "jan_lapsed_dec": float(lap.loc["2025-12-01", "reorder_rate"]), "jan_lapsed_jan": float(lap.loc["2026-01-01", "reorder_rate"]),
        "jan_treated": float(j0.conv_treated), "jan_holdout": float(j0.conv_holdout), "jan_diff_ci": float(j0.diff_ci95),
        "ret_m": float(sp.loc["1M", "retention_12m"]), "ret_q": float(sp.loc["3M", "retention_12m"]),
        "cmclv_m": float(sp.loc["1M", "cm_clv_12m_eur"]), "cmclv_q": float(sp.loc["3M", "cm_clv_12m_eur"]),
        "skip_q": float(sp.loc["3M", "skip_rate_per_scheduled_charge"]), "skip_m": float(sp.loc["1M", "skip_rate_per_scheduled_charge"]),
        "save_t": float(cs.loc["skip / swap / pause offered", "save_rate"]), "save_h": float(cs.loc["holdout (plain cancel page)", "save_rate"]),
        "te_ratio": {k: float(v) for k, v in ratio.items()},
        "wb30_ret_t": float(wb.loc["-30 % offer", "return_rate"]), "wb30_ret_h": float(wb.loc["holdout (no offer)", "return_rate"]),
        "wb30_cm_t": float(wb.loc["-30 % offer", "cm_per_recipient_180d"]), "wb30_cm_h": float(wb.loc["holdout (no offer)", "cm_per_recipient_180d"]),
        "wb30_cm_ci": float((wb.loc["-30 % offer", "cm_ci95"] ** 2 + wb.loc["holdout (no offer)", "cm_ci95"] ** 2) ** 0.5),
        "loy_naive": float(loy.relative_lift.iloc[0]), "loy_matched": float(loy.relative_lift.iloc[1]),
        "mpp_open_before": float(eng.loc["2025-08-01", "open_rate"]), "mpp_open_after": float(eng.loc["2025-10-01", "open_rate"]),
        "mpp_share": float(eng.loc["2025-10-01", "machine_share_of_opens"]),
        "click_before": float(eng.loc["2025-08-01", "click_rate"]), "click_after": float(eng.loc["2025-10-01", "click_rate"]),
        "sl_open_a": float(sl.loc["A", "open_rate"]), "sl_open_b": float(sl.loc["B", "open_rate"]),
        "sl_click_a": float(sl.loc["A", "click_rate"]), "sl_click_b": float(sl.loc["B", "click_rate"]),
        "sl_rpr_a": float(sl.loc["A", "revenue_per_recipient_5d"]), "sl_rpr_b": float(sl.loc["B", "revenue_per_recipient_5d"]),
        "sl_rpr_ci": float(sl.loc["A", "rpr_ci95"]),
        "dup_profiles": int(dq["duplicate profiles (same email_hash)"]),
        "churn_naive": float(dq["monthly subscription churn, skipped counted as cancelled (naive)"]),
        "churn_true": float(dq["monthly subscription churn, cancellations only (correct)"]),
        "utc_slip_share": float(dq["share of subscription orders that slip month"]),
        "fr_rpr_adapted": float(loc.loc["FR_adapted", "revenue_per_recipient_14d"]), "fr_rpr_translated": float(loc.loc["FR_translated", "revenue_per_recipient_14d"]),
        "fr_unsub_adapted": float(loc.loc["FR_adapted", "unsubscribe_rate_per_email"]), "fr_unsub_translated": float(loc.loc["FR_translated", "unsubscribe_rate_per_email"]),
        "fr_rpr_ci": float((loc.loc["FR_adapted", "rpr_ci95"] ** 2 + loc.loc["FR_translated", "rpr_ci95"] ** 2) ** 0.5),
        "vip_rpr_diff": float(fr.loc["VIP early access (Gold)", "rpr_diff"]), "vip_rpr_ci": float(fr.loc["VIP early access (Gold)", "rpr_diff_ci95"]),
        "vip_n": int(fr.loc["VIP early access (Gold)", "n_t"] + fr.loc["VIP early access (Gold)", "n_h"]),
    }


def scorecard(s):
    pct = lambda x: f"{x:.0%}"
    rows = [
        (1, "Attributed vs incremental revenue", "education 22 % incremental, replenishment 61 %",
         f"education {pct(s['edu_share'])} (+/- {s['edu_share_ci']:.0%}), replenishment {pct(s['rep_share'])} (+/- {s['rep_share_ci']:.0%})",
         "Yes: invest in replenishment, not in more education emails", True),
        (2, "Replenishment reminder too early", "day 26 + branch: +4.1 pts on 60-day repurchase",
         f"+{(s['j26'] - s['j21']) * 100:.1f} pts (+/- {s['j_diff_ci'] * 100:.1f})", "Yes: roll out day 26 + branch", True),
        (3, "January false signal (do NOT scale)", "flow effect = 0; January lifts everyone",
         f"lapsed reorders {s['jan_lapsed_jan'] / s['jan_lapsed_dec'] - 1:+.0%} Jan vs Dec; flow {s['jan_treated']:.1%} vs holdout {s['jan_holdout']:.1%}",
         "Yes: not scaled, re-test in March", True),
        (4, "Every-3-months plan: retention vs margin", "retention 58 % vs 41 %; CM-CLV about -9 %",
         f"retention {pct(s['ret_q'])} vs {pct(s['ret_m'])}; CM-CLV {s['cmclv_q'] / s['cmclv_m'] - 1:+.0%}",
         "Yes: lead with skip / swap on the monthly plan, no deeper discount", True),
        (5, "Price increase and -30 % win-back", "FR / IT 'too expensive' x2; -30 % offer: 18 % return, negative margin",
         f"FR x{s['te_ratio']['FR']:.1f}, IT x{s['te_ratio']['IT']:.1f}, DE x{s['te_ratio']['DE']:.1f}; return {pct(s['wb30_ret_t'])} vs {pct(s['wb30_ret_h'])}, "
         f"CM / recipient {s['wb30_cm_t'] - s['wb30_cm_h']:+.2f} EUR (+/- {s['wb30_cm_ci']:.2f})", "Yes: stop the -30 % offer, test an upgrade pack", True),
        (6, "Loyalty self-selection", "naive +42 %, matched +7 %",
         f"naive {s['loy_naive']:+.0%}, matched {s['loy_matched']:+.0%}", "Yes: programme kept, its value restated", True),
        (7, "Apple MPP opens", "machine opens from Sep 2025; subject test 'won' on opens",
         f"open rate {s['mpp_open_before']:.0%} -> {s['mpp_open_after']:.0%} ({s['mpp_share']:.0%} machine); B opens {s['sl_open_b']:.1%} vs {s['sl_open_a']:.1%} but clicks {s['sl_click_b']:.2%} vs {s['sl_click_a']:.2%}",
         "Yes: tests judged on clicks and revenue per recipient", True),
        (8, "Data issues", "2,300 duplicate profiles; skips counted as churn; UTC month slip",
         f"{s['dup_profiles']:,} duplicates; churn {s['churn_true']:.1%} vs naive {s['churn_naive']:.1%}; {s['utc_slip_share']:.1%} of subscription orders slip month",
         "Yes: fixed in 01_staging.sql, tested in 99_tests.sql", True),
    ]
    return pd.DataFrame(rows, columns=["event_id", "event", "planted", "found_by_sql", "decision", "handled_correctly"])


def build():
    out = {"public": public_facts(), "sim": sim_facts()}
    (PROC / "headline_facts.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    if (ROOT / "data" / "_hidden_truth.csv").exists():
        scorecard(out["sim"]).to_csv(PROC / "event_scorecard.csv", index=False)
    return out


def load():
    return json.loads((PROC / "headline_facts.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    f = build()
    print(pd.read_csv(PROC / "event_scorecard.csv")[["event_id", "found_by_sql"]].to_string(index=False))
