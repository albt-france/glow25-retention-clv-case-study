"""Self-contained interactive dashboard (one HTML file, Plotly embedded, works offline):
site/dashboard/index.html. Five tabs; every chart carries a PUBLIC DATA or SIMULATED tag in its title.

    python src/build_dashboard.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

import facts as facts_mod

ROOT = Path(__file__).resolve().parents[1]
PROC, PUB = ROOT / "data" / "processed", ROOT / "data" / "public"
OUT = ROOT / "site" / "dashboard" / "index.html"
BLUE, GREY, RED, GREEN, INK, MUTED = "#2A78D6", "#A3A19A", "#D03B3B", "#2E8B57", "#0B0B0B", "#52514E"
FOOT = "Independent case study based on public data · not affiliated with or endorsed by Glow25 / Primal State Performance GmbH"


def csv(n, folder=PROC):
    return pd.read_csv(folder / f"{n}.csv")


def style(fig, title, tag, h=360):
    color = "#1C5CAB" if tag.startswith("PUBLIC") else "#9A3B12"
    fig.update_layout(
        title=dict(text=f"{title}<br><span style='font-size:11px;color:{color}'><b>{tag}</b></span>", x=0.01, font=dict(size=14)),
        height=h, margin=dict(l=55, r=20, t=70, b=45), paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial", size=12, color=INK), legend=dict(orientation="h", y=-0.18),
        hoverlabel=dict(font_family="Segoe UI"))
    fig.update_xaxes(gridcolor="#E1E0D9", zeroline=False)
    fig.update_yaxes(gridcolor="#E1E0D9", zeroline=False)
    return json.loads(fig.to_json())


# ------------------------------------------------------------------ tab 2: market & offer (PUBLIC DATA)
def tab_market():
    e = csv("eurostat_isoc_ec_ibgs", PUB)
    f = e[e.ind_type == "F_Y25_54"].pivot_table(index="geo", columns="indic_is", values="value").sort_values("I_BMED1", ascending=False)
    eu = go.Figure([go.Bar(name="Medicines or supplements (I_BMED1)", x=f.index, y=f.I_BMED1, marker_color=BLUE),
                    go.Bar(name="Cosmetics, beauty, wellness (I_BCBW)", x=f.index, y=f.I_BCBW, marker_color=GREY)])
    eu.update_yaxes(title="% of women 25-54, bought online in last 3 months")
    w = csv("wikipedia_collagen_pageviews", PUB)
    w["date"] = pd.to_datetime(w.month.astype(str), format="%Y%m")
    w["index"] = w.views / w.groupby("project").views.transform("mean")
    wk = go.Figure([go.Scatter(x=g.date, y=g["index"], name=p.replace(".wikipedia", ""), mode="lines") for p, g in w.groupby("project")])
    wk.update_yaxes(title="monthly views / project average")
    cat = csv("glow25_catalogue", PUB)
    cat["group"] = cat.type.fillna("Other").map(lambda t: "Supplement" if "Supplement" in t or "Collagen" in t or "Kollagen" in t else t)
    g = cat.groupby(["group", "subscribable"]).size().unstack(fill_value=0)
    cb = go.Figure([go.Bar(name="subscribable (-15 % monthly / -25 % every 3 months)", y=g.index, x=g.get(True, 0), orientation="h", marker_color=BLUE),
                    go.Bar(name="not subscribable (incl. 225 g trial packs)", y=g.index, x=g.get(False, 0), orientation="h", marker_color=GREY)])
    cb.update_layout(barmode="stack")
    return [style(eu, "France buys beauty online, not supplements: the FR angle is the beauty ritual", "PUBLIC DATA · Eurostat isoc_ec_ibgs, 2024, extracted 2026-11-24, no status flags"),
            style(wk, "Interest in collagen peaks every January in all five languages", "PUBLIC DATA · Wikimedia pageviews (user agents), Nov 2023 - Oct 2026"),
            style(cb, "29 products: 8 can be subscribed; trial packs cannot, so they need a bridge flow", "PUBLIC DATA · glow25.de /products/<handle>.js, read 2026-11-24")]


# ------------------------------------------------------------------ tab 3: cohorts & CLV
def tab_cohorts():
    c = csv("cohort_retention")
    c = c[c.month_index.between(1, 12)]
    hm = c.pivot(index="cohort_month", columns="month_index", values="active_share")
    heat = go.Figure(go.Heatmap(z=hm.values, x=[f"M{k}" for k in hm.columns], y=hm.index, colorscale="Blues", zmin=0, zmax=0.6,
                                hovertemplate="cohort %{y}<br>%{x}: %{z:.1%}<extra></extra>", colorbar=dict(tickformat=".0%")))
    seg = csv("cohort_cmclv_by_segment")
    s1 = seg[seg.dimension == "first order type"].sort_values("cm_clv_12m")
    bars = go.Figure([go.Bar(x=s1.cm_clv_12m, y=s1.segment, orientation="h", marker_color=BLUE, text=s1.cm_clv_12m.round(0), textposition="outside")])
    bars.update_xaxes(title="EUR contribution margin per customer, first 12 months")
    rs, ru = csv("kpi_repurchase"), csv("uci_repurchase")
    rs = rs[rs.segment == "all"]
    rep = go.Figure([go.Scatter(x=rs.n_days, y=rs.repurchase_rate, name="Brand G (SIMULATED)", mode="lines+markers", line_color=RED),
                     go.Scatter(x=ru.n_days, y=ru.repurchase_rate, name="UCI UK retailer (PUBLIC DATA, method demo)", mode="lines+markers", line_color=BLUE)])
    rep.update_yaxes(tickformat=".0%", title="2nd order within N days")
    rep.update_xaxes(title="days after first order")
    bt = csv("clv_uci_backtest")
    btf = go.Figure(go.Bar(x=bt.method, y=bt.revenue_jul_nov_2011_gbp, marker_color=[BLUE, GREY, INK],
                           text=[f"{v:+.0%}" if m != "Actual (what happened)" else "actual" for m, v in zip(bt.method, bt.error_vs_actual)], textposition="outside"))
    btf.update_yaxes(title="GBP, Jul-Nov 2011")
    return [style(heat, "Monthly cohorts: share of customers ordering in month k", "SIMULATED · Brand G"),
            style(bars, "A first order on subscription is worth almost 3x a trial pack in 12-month margin", "SIMULATED · Brand G, cohorts Nov 2024 - Oct 2025"),
            style(rep, "Repurchase curves: same SQL on simulated data and on real transactions", "SIMULATED + PUBLIC DATA (UCI Online Retail II, UK online retailer, method demo)"),
            style(btf, "Back-test: both CLV models miss the autumn peak by about 20 %", "PUBLIC DATA · UCI Online Retail II (CC BY 4.0), fit to June 2011")]


# ------------------------------------------------------------------ tab 4: flows & real lift
def tab_flows(f):
    fr = csv("flow_holdout_readout")
    fr = fr[fr.attributed_revenue_eur.fillna(0) > 0].sort_values("attributed_eur_all_period", ascending=False)
    lift = go.Figure([go.Bar(name="Attributed (last touch: click 5 d / open 1 d)", x=fr.flow, y=fr.attributed_revenue_eur, marker_color=GREY),
                      go.Bar(name="Incremental (vs 10 % holdout), 95 % CI", x=fr.flow, y=fr.incremental_revenue_eur, marker_color=BLUE,
                             error_y=dict(type="data", array=fr.incremental_revenue_ci95, color=INK))])
    lift.update_yaxes(title="EUR, entries with a complete window")
    gap = csv("reorder_gap_distribution")
    gh = go.Figure(go.Bar(x=gap.gap_days, y=gap.reorders, marker_color=BLUE))
    for d, lab, col, pos in ((21, "day 21", RED, "top left"), (26, "day 26", GREEN, "top right")):
        gh.add_vline(x=d, line_dash="dash", line_color=col, annotation_text=lab, annotation_position=pos)
    gh.update_xaxes(title="days between two one-off orders of a 30-day jar", range=[0, 90])
    rj = csv("replenishment_j21_vs_j26")
    jb = go.Figure(go.Bar(x=rj.arm, y=rj.repurchase_60d, marker_color=[BLUE, GREEN, GREY], error_y=dict(type="data", array=rj.repurchase_ci95),
                          text=[f"{v:.1%}" for v in rj.repurchase_60d], textposition="inside", insidetextanchor="start"))
    jb.update_yaxes(tickformat=".0%", title="60-day repurchase", range=[0.4, 0.62])
    lap = csv("lapsed_reactivation_by_month")
    wj = csv("winback_january_readout")
    j0 = wj[wj.entry_month.str.startswith("2026-01")].iloc[0]
    jan = go.Figure([go.Scatter(x=lap.month, y=lap.reorder_rate, name="lapsed customers reordering in the month (all)", mode="lines+markers", line_color=GREY),
                     go.Bar(x=["2026-01-15", "2026-01-20"], y=[j0.conv_treated, j0.conv_holdout], name="January entrants: flow vs holdout (30 d)",
                            marker_color=[BLUE, RED], width=4 * 86400000, text=["flow", "holdout"], textposition="outside")])
    jan.add_vline(x="2026-01-02", line_dash="dot", line_color=INK, annotation_text="win-back launched")
    jan.update_yaxes(tickformat=".1%")
    return [style(lift, "Education claims the most revenue; only about a fifth of it is incremental", "SIMULATED · Brand G, holdout read-out", 400),
            style(gh, "One-off buyers reorder around day 32-34: a day-21 reminder comes too early", "SIMULATED · jar duration from the public catalogue (450 g, 15 g servings)"),
            style(jb, "Day 26 + 'still have some?' branch beats day 21 by about 4.6 points", "SIMULATED · concurrent A/B, triggers Feb - May 2026"),
            style(jan, "January false signal: reorders rise with or without the new win-back flow", "SIMULATED · do not scale; re-test in March")]


# ------------------------------------------------------------------ tab 5: subscriptions, loyalty, data quality
def tab_subs(f):
    cu = csv("sub_retention_curve")
    rc = go.Figure([go.Scatter(x=g.day, y=g.still_active, name={"1M": "monthly -15 %", "3M": "every 3 months -25 %"}[k], mode="lines+markers",
                               line_color=BLUE if k == "1M" else GREY) for k, g in cu.groupby("interval")])
    rc.update_yaxes(tickformat=".0%", title="still active")
    rc.update_xaxes(title="days since start")
    sp = csv("sub_plan_economics")
    cm = go.Figure(go.Bar(x=["monthly -15 %", "every 3 months -25 %"], y=sp.cm_clv_12m_eur, marker_color=[BLUE, GREY],
                          text=[f"EUR {v:.0f} · retention {r:.0%}" for v, r in zip(sp.cm_clv_12m_eur, sp.retention_12m)], textposition="outside"))
    cm.update_yaxes(title="CM-CLV 12 months (EUR)", range=[0, 200])
    pr = csv("price_increase_too_expensive")
    pi = go.Figure([go.Bar(name=p, x=g.market, y=g.per_1000_active, marker_color=GREY if p.startswith("Oct") else RED) for p, g in pr.groupby("period", sort=False)])
    pi.update_yaxes(title="'too expensive' cancellations per 1,000 active subs / month")
    loy = csv("loyalty_naive_vs_matched")
    lb = go.Figure(go.Bar(x=["naive", "matched (cohort, market, prior orders)"], y=loy.relative_lift, marker_color=[GREY, BLUE],
                          text=[f"{v:+.0%}" for v in loy.relative_lift], textposition="outside"))
    lb.update_yaxes(tickformat=".0%", title="members vs non-members, 180-day reorder", range=[0, 0.55])
    en = csv("email_monthly_engagement")
    mp = go.Figure([go.Scatter(x=en.month, y=en.open_rate, name="open rate (as reported)", line_color=RED),
                    go.Scatter(x=en.month, y=en.open_rate_excl_machine, name="open rate without machine opens", line_color=GREY),
                    go.Scatter(x=en.month, y=en.click_rate, name="click rate", line_color=BLUE, yaxis="y2")])
    mp.update_layout(yaxis=dict(tickformat=".0%"), yaxis2=dict(tickformat=".1%", overlaying="y", side="right", showgrid=False))
    dq = csv("data_quality_summary")
    dqt = go.Figure(go.Table(header=dict(values=["Check", "Value"], fill_color="#F2EFE9", align="left"),
                             cells=dict(values=[dq.check_name, [f"{v:.1%}" if v < 1 else f"{v:,.0f}" for v in dq.value]], align="left", height=26)))
    return [style(rc, "The every-3-months plan keeps more subscribers...", "SIMULATED · subscriptions started Nov 2024 - Oct 2025"),
            style(cm, "...but the monthly plan earns more margin per subscriber", "SIMULATED · 12-month contribution margin"),
            style(pi, "After the +10 % price rise, 'too expensive' cancellations about doubled in FR and IT, not in DE", "SIMULATED · Oct 2025 - Sep 2026"),
            style(lb, "Loyalty members look +42 % better; matched, the gap shrinks to about +10 %", "SIMULATED · one-off orders Jan 2025 - Apr 2026"),
            style(mp, "Machine opens inflate open rates from September 2025; clicks do not move", "SIMULATED · Apple Mail Privacy Protection"),
            style(dqt, "Data issues fixed in staging", "SIMULATED · 01_staging.sql, 99_tests.sql", 300)]


def overview(f):
    s, p = f["sim"], f["public"]
    sc = csv("event_scorecard")
    tiles = [
        ("Products / subscribable", f"{p['catalogue_products']} / {p['subscribable_products']}", "-15 % monthly, -25 % every 3 months; trial packs not subscribable", "PUBLIC DATA"),
        ("Education flow: incremental share", f"{s['edu_share']:.0%}", f"of EUR {s['edu_attributed'] / 1000:.0f}k attributed revenue (95 % CI +/- {s['edu_share_ci']:.0%})", "SIMULATED"),
        ("Replenishment day 26 vs day 21", f"+{(s['j26'] - s['j21']) * 100:.1f} pts", "60-day repurchase, concurrent A/B", "SIMULATED"),
        ("Monthly vs 3-monthly plan", f"{s['cmclv_m']:.0f} vs {s['cmclv_q']:.0f} EUR", f"12-month CM-CLV; retention {s['ret_m']:.0%} vs {s['ret_q']:.0%}", "SIMULATED"),
    ]
    return tiles, sc


def main():
    f = facts_mod.build()
    figs = {"t2": tab_market(), "t3": tab_cohorts(), "t4": tab_flows(f), "t5": tab_subs(f)}
    tiles, sc = overview(f)
    tile_html = "".join(f'<div class="tile"><div class="lab">{a} <span class="tag {"pub" if d.startswith("PUBLIC") else "sim"}">{d}</span></div>'
                        f'<div class="big">{b}</div><div class="txt">{c}</div></div>' for a, b, c, d in tiles)
    rows = "".join(f"<tr><td>{r.event_id}</td><td>{r.event}</td><td>{r.found_by_sql}</td><td>{r.decision}</td></tr>" for r in sc.itertuples())
    decisions = ["Report incremental contribution margin per flow (10 % holdout) next to attributed revenue.",
                 "Move the replenishment reminder to day 26 with a 'still have some?' branch.",
                 "Bridge 225 g trial packs to the subscription with a 3-email flow.",
                 "Save subscriptions with skip / swap / pause; stop the -30 % comeback offer; test an upgrade pack.",
                 "Localise: FR flows lead with the beauty ritual (Eurostat), one brand voice everywhere."]
    divs = {k: "".join(f'<div class="chart" id="{k}_{i}" style="height:{fg["layout"].get("height", 360)}px"></div>' for i, fg in enumerate(v))
            for k, v in figs.items()}
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Glow25 retention case study - dashboard</title>
<style>
body {{ margin:0; font-family:'Segoe UI',Arial,sans-serif; background:#F2EFE9; color:#0B0B0B; }}
header {{ padding:18px 28px 8px; }} h1 {{ font-size:22px; margin:0 0 4px; }} .sub {{ color:#52514E; font-size:13.5px; margin:0; }}
nav {{ display:flex; gap:6px; padding:8px 28px; flex-wrap:wrap; }}
nav button {{ border:1px solid #D9D6CF; background:#fff; padding:8px 14px; border-radius:6px; cursor:pointer; font:inherit; font-size:13.5px; }}
nav button.on {{ background:#0B0B0B; color:#fff; border-color:#0B0B0B; }}
.tab {{ display:none; padding:8px 28px 24px; }} .tab.on {{ display:block; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(520px,1fr)); gap:14px; }}
.chart, .card, .tile {{ background:#fff; border:1px solid #E1DDD4; border-radius:8px; }} .card, .tile {{ padding:6px; }} .chart {{ overflow:hidden; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:12px; margin-bottom:14px; }}
.tile {{ padding:12px 14px; }} .lab {{ font-size:12px; font-weight:700; color:#52514E; }} .big {{ font-size:30px; font-weight:700; margin:4px 0; }}
.txt {{ font-size:12.5px; color:#52514E; }} .tag {{ font-size:10px; font-weight:700; padding:2px 6px; border-radius:3px; }}
.pub {{ background:#E3EEFB; color:#1C5CAB; }} .sim {{ background:#FBE9E0; color:#9A3B12; }}
.card {{ padding:12px 16px; }} .card h2 {{ font-size:15px; margin:0 0 8px; }} table {{ border-collapse:collapse; width:100%; font-size:12.5px; }}
th, td {{ text-align:left; border-bottom:1px solid #EFECE6; padding:5px 6px; vertical-align:top; }} th {{ color:#52514E; }}
li {{ font-size:13.5px; margin:4px 0; }} footer {{ padding:10px 28px 24px; color:#898781; font-size:11.5px; }}
</style></head><body>
<header><h1>Glow25: retention as a system - which customers stay, which flows really earn, and what to change first</h1>
<p class="sub">Public data on Glow25 (offer, markets, claim rules) and the market (Eurostat, Wikipedia), a method demo on real transactions (UCI),
and a SIMULATED collagen brand ("Brand G") for the day-to-day of the job. Simulated numbers are never Glow25's.</p></header>
<nav>{''.join(f'<button data-t="{k}" class="{"on" if k == "t1" else ""}">{n}</button>' for k, n in
              [("t1", "1 · Overview"), ("t2", "2 · Market & offer"), ("t3", "3 · Cohorts & CLV"), ("t4", "4 · Flows & real lift"),
               ("t5", "5 · Subscriptions, loyalty & data quality")])}</nav>
<section id="t1" class="tab on"><div class="tiles">{tile_html}</div>
<div class="grid"><div class="card"><h2>Five decisions</h2><ol>{''.join(f'<li>{d}</li>' for d in decisions)}</ol>
<p class="txt">Method: public facts collected politely (robots.txt, 1 request / 3 s, cached once); DuckDB SQL with tests; a simulated brand with 8 planted
events to find; every view tagged PUBLIC DATA or SIMULATED.</p></div>
<div class="card"><h2>Eight planted events: what the SQL found <span class="tag sim">SIMULATED</span></h2>
<table><tr><th>#</th><th>Event</th><th>Found</th><th>Decision</th></tr>{rows}</table></div></div></section>
{''.join(f'<section id="{k}" class="tab"><div class="grid">{divs[k]}</div></section>' for k in figs)}
<footer>{FOOT}. Sources and method: README and the PDF report (page 6).</footer>
<script>{get_plotlyjs()}</script>
<script>
const FIGS = {json.dumps(figs)};
const drawn = {{}};
function draw(t) {{ if (drawn[t] || !FIGS[t]) return; FIGS[t].forEach((f, i) => Plotly.newPlot(t + '_' + i, f.data, Object.assign(JSON.parse(JSON.stringify(f.layout)), {{autosize: true}}), {{responsive: true, displaylogo: false}})); drawn[t] = true; }}
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {{
  document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
  document.querySelectorAll('.tab').forEach(s => s.classList.toggle('on', s.id === b.dataset.t));
  draw(b.dataset.t); window.dispatchEvent(new Event('resize'));
}});
</script></body></html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"written {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
