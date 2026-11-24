"""Build the 7-page PDF report (pages 0-6): HTML (grey-beige page, white cards) printed by Edge/Chrome headless.
Numbers are read from data/public and data/processed (src/facts.py). The HTML draft and chart images live in
data/raw/report/ (not published); the PDF goes to site/report/.

    python src/build_pdf.py
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pandas as pd
from pypdf import PdfReader, PdfWriter

import charts
import facts as facts_mod

ROOT = Path(__file__).resolve().parents[1]
PROC, BUILD = ROOT / "data" / "processed", ROOT / "data" / "raw" / "report"
PDF = ROOT / "site" / "report" / "glow25_retention_case_study.pdf"
DISCLAIMER = "Independent case study based on public data · not affiliated with or endorsed by Glow25 / Primal State Performance GmbH"
# the AI note is written once, in the README (Methods), and quoted here word for word
AI_NOTE = next(line[2:].strip() for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
               if line.startswith("- AI-assisted workflow"))


def page(n, title, subtitle, tags, body, sources):
    t = "".join(f'<div class="tag tag-{x.lower().split()[0]}">{x}</div>' for x in tags)
    return f"""<section class="page"><header><div><h1>{title}</h1><p class="sub">{subtitle}</p></div><div class="tags">{t}</div></header>
<main>{body}</main><footer><span>{sources}</span><span>{DISCLAIMER}</span><span>{n} / 6</span></footer></section>"""


def card(inner, cls=""):
    return f'<div class="card {cls}">{inner}</div>'


def img(src):
    return f'<figure><img src="{src}"/></figure>'


def tile(label, value, text, tag):
    return card(f'<div class="label">{label} <span class="mini mini-{tag.lower().split()[0]}">{tag}</span></div>'
                f'<div class="big">{value}</div><p>{text}</p>', "tile")


def eur(x):
    return f"EUR {x:,.0f}"


# ------------------------------------------------------------------ pages
def p0(f, ch):
    s, p = f["sim"], f["public"]
    qs = card("""<h2>Five questions</h2><ol class="qs">
<li><b>1</b>What does Glow25 sell, where, and what does the job ask for? <span class="pg">p.1</span></li>
<li><b>2</b>What do the offer, the markets, the season and the claim rules imply for retention? <span class="pg">p.2</span></li>
<li><b>3</b>Who stays, and what is each customer worth in contribution margin? <span class="pg">p.3</span></li>
<li><b>4</b>Which flows really earn, once attributed revenue is checked against a holdout? <span class="pg">p.4</span></li>
<li><b>5</b>How to keep subscribers and read loyalty and email data without fooling ourselves? <span class="pg">p.5</span></li></ol>
<h2 style="margin-top:14px">What comes with it</h2><ul class="small">
<li><b>Excel workbook</b> (real formulas): order margin, monthly vs 3-monthly plan, flow holdouts with intervals, sample size, checks.</li>
<li><b>Interactive dashboard</b> (one HTML file, 5 tabs): overview, market &amp; offer, cohorts &amp; CLV, flows &amp; real lift, subscriptions &amp; data quality.</li>
<li><b>SQL</b> (DuckDB, 12 files + tests): staging fixes, KPIs, cohorts, CM, holdout read-outs, timing, subscriptions, traps, UCI demo.</li>
<li><b>Docs</b>: retention strategy, 8 Klaviyo flow specs, experiment playbook, KPI dictionary, localisation playbook, weekly update, claims guardrail.</li>
<li><b>Copy</b>: 4 flows x 2 emails written in English + French adaptations, all claims-checked.</li></ul>""")
    tiles = "".join([
        tile("Offer", f"{p['catalogue_products']} / {p['subscribable_products']}", "products / subscribable (-15 % monthly, -25 % every 3 months); "
             "the 225 g trial packs cannot be subscribed: they need a bridge flow.", "PUBLIC DATA"),
        tile("Education flow, real share", f"{s['edu_share']:.0%}", f"of {eur(s['edu_attributed'])} attributed revenue is incremental vs its "
             f"10 % holdout (95 % CI +/- {s['edu_share_ci']:.0%}). Most clickers would have reordered anyway.", "SIMULATED"),
        tile("Replenishment timing", f"+{(s['j26'] - s['j21']) * 100:.1f} pts", f"60-day repurchase, day 26 + branch vs day 21 "
             f"({s['j26']:.1%} vs {s['j21']:.1%}), concurrent A/B.", "SIMULATED"),
        tile("Monthly vs 3-monthly plan", f"{s['cmclv_m']:.0f} vs {s['cmclv_q']:.0f}", f"EUR 12-month CM-CLV; the 3-monthly plan keeps more "
             f"({s['ret_q']:.0%} vs {s['ret_m']:.0%}) but earns less.", "SIMULATED"),
    ])
    reco = card("""<h2>Five decisions</h2><ol class="reco">
<li><b>Report incremental contribution margin per flow</b> (permanent 10 % holdout) next to attributed revenue; move effort from education to replenishment.</li>
<li><b>Replenishment on day 26 with a "still have some?" branch</b>, then personal timing from each customer's own reorder gap.</li>
<li><b>Bridge the 225 g trial pack to the subscription</b> with a 3-email flow that ends before the 15 servings run out.</li>
<li><b>Save subscribers with skip / swap / pause, not discounts</b>: show the monthly plan first, stop the -30 % comeback offer, test an upgrade pack.</li>
<li><b>Localise, do not translate</b>: FR flows lead with the beauty ritual; one brand voice; every claim from the authorised list only.</li></ol>""")
    how = card("""<h2>Method in three lines</h2><p><b>Public data</b> on Glow25 (offer, markets, claim rules), Eurostat and Wikipedia, plus a CLV method demo on real
transactions (UCI). <b>Simulated data</b> for a fictional collagen brand, "Brand G", with 8 planted events to find. DuckDB SQL with tests, Excel with
formulas, Plotly dashboard; every view tagged PUBLIC DATA or SIMULATED - simulated numbers are never Glow25's.</p>""", "auto")
    body = f'<div class="g0"><div class="stack">{qs}{how}</div><div class="stack"><div class="grid2t">{tiles}</div>{reco}</div></div>'
    return page(0, "Glow25: retention as a system - which customers stay, which flows really earn, and what to change first",
                "For a collagen brand that sells on subscription: which lifecycle moments create value in contribution margin, not in attributed revenue, "
                "and how to build and test them across seven markets.", ["OVERVIEW"], body,
                "Sources: page 6 · README")


def p1(f, ch):
    p = f["public"]
    facts = card(f"""<h2>Published facts (read 2026-11-24)</h2><ul class="facts small">
<li>Brand of <b>Primal State Performance GmbH</b>, Berlin (Amtsgericht Charlottenburg, HRB 192319 B; legal notice on glow25.de).</li>
<li><b>Shopify</b> store (glow25-de.myshopify.com) with <b>Recharge</b> subscriptions and <b>Klaviyo</b> blocks visible in the public HTML.</li>
<li><b>{len(p['markets_hreflang'])} markets</b> in <code>hreflang</code>: {', '.join(p['markets_hreflang'])} (country domains .fr .it .nl .es .co.uk; BE on .nl).</li>
<li><b>{p['catalogue_products']} products</b>: {p['subscribable_products']} subscribable (all with "Monatliche Lieferung" -15 % and "Lieferung alle 3 Monate" -25 %),
{p['not_subscribable_products']} not (bundles, cosmetics, accessories, 225 g trial packs at EUR 14.99 / 19.99), {p['free_items']} free gifts.</li>
<li>Magazine: {p['articles_per_domain']} articles in the sitemap of each of {p['domains_with_articles']} country sitemaps.</li>
<li>{p['open_jobs']} open roles on Ashby; this one published {p['job_published'][:10]}, full time, "Remote - Europe Only", no salary published.</li></ul>""")
    stated = card("""<h2>As stated by Glow25 (quoted, not verified)</h2><ul class="facts small">""" + "".join(
        f'<li>"{x["text"]}" - {x["where"]}.</li>' for x in p["stated"]) + "</ul>")
    rows = [("Retention strategy across the lifecycle", "Lifecycle map with one KPI and one owner per stage; 5 priorities (p.3-5, docs/retention_strategy.md)"),
            ("Subscription & loyalty: sign-up, churn prevention, VIP", "Trial-pack bridge, monthly vs 3-monthly margin, skip / swap / pause save rate, loyalty bias (p.3, p.5)"),
            ("Klaviyo flows built end to end", "8 flow specs: trigger, filters, delays, splits, exclusions, holdout, stop rule (docs/klaviyo_flow_specs.md)"),
            ("Direct-response copy and campaigns", "4 flows x 2 emails written in English, January and Black Friday calendar, claims-checked (copy/)"),
            ("Decisions on cohorts, repeat rate, contribution margin; real lift vs attributed", "CM-CLV by cohort, holdout read-outs with intervals, January trap (p.3-4)"),
            ("AI in practice, human judgement on claims; localisation", "Copy lab with optional language-model step + claims guardrail; FR adaptation test (p.5, docs/)")]
    job = card("<h2>The six missions of the job, and what this study shows for each</h2><table><tr><th>Mission (job posting)</th><th>Shown here</th></tr>"
               + "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows) + "</table>")
    first = card("""<h2>First 30 days in the role (plan)</h2><ol class="small">
<li>Audit the live Klaviyo flows and campaigns; add a permanent 10 % holdout to each flow; agree KPI definitions with Analytics.</li>
<li>Read each flow on incremental contribution margin; move effort from what claims revenue to what earns it.</li>
<li>Ship the quick wins: replenishment timing (day 26 + branch), trial-pack bridge, skip / swap / pause before cancel.</li>
<li>Start the weekly retention update shared with Acquisition, CX, Product and Analytics.</li></ol>""", "auto")
    life = card("""<h2>Lifecycle map: one KPI and one owner per stage</h2><table class="small"><tr><th>Stage</th><th>Flow / lever</th><th>KPI</th></tr>
<tr><td>First order</td><td>Welcome (F1)</td><td>14-day revenue per recipient; unsubscribes</td></tr>
<tr><td>Education</td><td>Post-purchase education (F2)</td><td>incremental 45-day revenue vs holdout</td></tr>
<tr><td>Trial -> full size</td><td>Trial pack -> subscription (F3)</td><td>subscription starts within 30 days</td></tr>
<tr><td>Replenishment</td><td>Day 26 + branch (F4)</td><td>60-day repurchase, incremental</td></tr>
<tr><td>Subscription</td><td>Onboarding (F5), cancel-save (F6)</td><td>monthly churn (skips excluded); save rate</td></tr>
<tr><td>Loyalty / VIP</td><td>Gold tier, early access (F8)</td><td>matched reorder lift; CM per member</td></tr>
<tr><td>Win-back</td><td>90-day lapse (F7), seasonal campaigns</td><td>incremental 30-day reorder; CM</td></tr></table>
<p class="small">Owner: the Retention &amp; CLV Operator, with Creative (copy, visuals), CX (cancel reasons), Product (launches) and Analytics (data).</p>""")
    body = f'<div class="grid-1-1"><div class="stack">{facts}{stated}{first}</div><div class="stack">{job}{life}</div></div>'
    return page(1, "Glow25 sells a subscription-ready collagen range in seven markets - the job is to turn first orders into margin",
                "What is public about the company and its stack, and how each mission of the Retention & CLV Operator posting is covered by this study.",
                ["PUBLIC DATA"], body, "glow25.de (legal notice, home page, products, sitemaps) · Ashby public job board API")


def p2(f, ch):
    p = f["public"]
    rule = card(f"""<h2>The claim rule for collagen <span class="mini mini-public">PUBLIC DATA</span></h2>
<p>Regulation (EU) No 432/2012 has <b>no claim for collagen itself</b>. "Collagen" appears only in {p['authorised_collagen_claims_en']} vitamin C claims, e.g.:</p>
<p class="quote">Vitamin C contributes to normal collagen formation for the normal function of skin.</p>
<p class="small">Same wording for blood vessels, bones, cartilage, gums, teeth. That is why "mit Vitamin C" matters in the offer. Every email in this study passes
<code>claims_check.py</code> (authorised wordings only, EN and FR) and a person. Not legal advice.</p>""")
    so = card(f"""<h2>What it means for retention</h2><ul class="facts small">
<li><b>Subscription is the core</b>: 8 products, two plans (-15 % / -25 %): plan choice is a margin decision (p.3).</li>
<li><b>Trial packs are the bridge</b>: 15 servings, not subscribable -> a flow must convert before they run out.</li>
<li><b>France needs a beauty angle</b>: {p['eurostat_beauty_f25_54']['FR']:.1f} % of women 25-54 bought beauty online, {p['eurostat_supplements_f25_54']['FR']:.1f} % supplements.</li>
<li><b>January is the peak</b>: views in January are {min(p['wiki_jan_over_jul'].values()):.1f}-{max(p['wiki_jan_over_jul'].values()):.1f}x July: plan launches, and never read a January test without a holdout.</li></ul>""")
    body = f"""<div class="grid2"><div class="stack">{card(img(ch['offer']))}{card(img(ch['wiki']))}</div>
<div class="stack">{card(img(ch['eurostat']))}<div class="grid2t">{rule}{so}</div></div></div>"""
    return page(2, "The offer is built for subscription, France buys beauty not supplements, and January is the peak",
                "Glow25's public offer and the market around it: plan discounts, trial packs, online buying by country, seasonality and the claim rule.",
                ["PUBLIC DATA"], body, "glow25.de products (2026-11-24) · Eurostat isoc_ec_ibgs (2024, updated 2026-04-17) · Wikimedia pageviews · Regulation (EU) 432/2012")


def p3(f, ch):
    s, p = f["sim"], f["public"]
    rp = {str(k): v for k, v in s["repurchase"].items()}
    uci = card(f"""<h2>Method check on real transactions <span class="mini mini-public">PUBLIC DATA</span></h2>
<p class="small">UCI Online Retail II (UK online retailer, 2009-2011, CC BY 4.0): {p['uci_rows_raw']:,} rows -> {p['uci_customers']:,} customers,
{p['uci_invoices']:,} invoices after removing returns, missing ids and duplicates. Fit to June 2011, predict July-November:
<b>BG/NBD + Gamma-Gamma {p['uci_backtest_error_bgnbd']:+.0%}</b>, <b>empirical cohorts {p['uci_backtest_error_empirical']:+.0%}</b> vs actual.
Both miss the autumn peak: neither knows the season - the same reason January matters for collagen.
Not Glow25 customers; a method demo only.</p>""")
    read = card(f"""<h2>Reading <span class="mini mini-simulated">SIMULATED</span></h2><ul class="facts small">
<li>Repurchase after a first order: {rp['30']:.0%} in 30 days, {rp['60']:.0%} in 60, {rp['180']:.0%} in 180.</li>
<li>A first order on subscription is worth about 3x a trial pack in 12-month margin: acquisition should bid on CM-CLV by first product.</li>
<li>Monthly -15 % vs every 3 months -25 %: retention {s['ret_m']:.0%} vs {s['ret_q']:.0%}, but CM-CLV {eur(s['cmclv_m'])} vs {eur(s['cmclv_q'])}:
deeper discount, heavier 3-jar parcel, {s['skip_q']:.0%} of 3-monthly charges skipped (stock at home).</li>
<li><b>Decision</b>: show the monthly plan first with skip / swap / pause; no deeper discount.</li></ul>""")
    body = f"""<div class="grid3">{card(img(ch['cmclv']))}{card(img(ch['repurchase']))}{card(img(ch['subcurves']))}</div>
<div class="grid2 short">{read}{uci}</div>"""
    return page(3, "Subscribers are worth the most - but the plan that keeps them longest is not the one that earns most",
                "Cohorts, repurchase and contribution-margin CLV on the simulated brand; the same SQL and a CLV back-test on real transactions.",
                ["SIMULATED", "PUBLIC DATA"], body, "sql/02, 03, 07, 11 · src/clv.py · excel/retention_economics.xlsx (Subscription_Scenarios)")


def p4(f, ch):
    s = f["sim"]
    a = card(f"""<h2>Attributed is not incremental</h2><ul class="facts small">
<li>Education flow: {eur(s['edu_attributed_all'])} attributed over 2 years; vs its holdout only <b>{s['edu_share']:.0%}</b> is incremental
({eur(s['edu_incremental'])} +/- {eur(s['edu_incremental_ci'])}).</li>
<li>Replenishment: <b>{s['rep_share']:.0%}</b> incremental (+/- {s['rep_share_ci']:.0%}). Same budget, very different value.</li>
<li>Rule: every flow keeps a 10 % holdout; decisions on incremental contribution margin.</li></ul>""")
    b = card(f"""<h2>Timing and the January trap</h2><ul class="facts small">
<li>Median reorder gap {s['gap_median']:.0f} days; only {s['gap_before21']:.1%} reorder before day 21. Day 26 + branch: {s['j26']:.1%} vs {s['j21']:.1%}
(holdout {s['j_hold']:.1%}); clicks {s['j26_click']:.1%} vs {s['j21_click']:.1%}. <b>Roll out.</b></li>
<li>Win-back launched 2 Jan 2026: lapsed reorders {s['jan_lapsed_jan'] / s['jan_lapsed_dec'] - 1:+.0%} vs December - but the holdout rose too
({s['jan_treated']:.1%} flow vs {s['jan_holdout']:.1%} holdout). <b>Not scaled; re-test in March.</b></li></ul>""")
    body = f"""<div class="grid-2-1"><div class="stack">{card(img(ch['lift']))}</div><div class="stack">{a}{b}</div></div>
<div class="grid3">{card(img(ch['gaps']))}{card(img(ch['j26']))}{card(img(ch['january']))}</div>"""
    return page(4, "The flow that claims the most earns the least: replenishment at day 26 beats more education emails",
                "Eight flows read against permanent 10 % holdouts: attributed vs incremental revenue, reminder timing, and a January signal that is not real.",
                ["SIMULATED"], body, "sql/05, 06, 08 · docs/klaviyo_flow_specs.md · docs/experiment_playbook.md · copy/03_replenishment_j26.md")


def p5(f, ch):
    s = f["sim"]
    subs = card(f"""<h2>Keeping subscribers</h2><ul class="facts small">
<li>Skip / swap / pause before cancel: save rate <b>{s['save_t']:.0%}</b> vs {s['save_h']:.0%} on a plain cancel page.</li>
<li>+10 % price (April 2026): "too expensive" cancellations x{s['te_ratio']['FR']:.1f} in FR, x{s['te_ratio']['IT']:.1f} in IT, x{s['te_ratio']['DE']:.1f} in DE.</li>
<li>-30 % comeback offer: {s['wb30_ret_t']:.0%} return vs {s['wb30_ret_h']:.0%} without it, but CM per recipient over 6 months
{s['wb30_cm_t'] - s['wb30_cm_h']:+.2f} EUR (+/- {s['wb30_cm_ci']:.2f}). <b>Stop; test an upgrade pack.</b></li></ul>""")
    traps = card(f"""<h2>Traps in the data</h2><ul class="facts small">
<li><b>Loyalty</b>: members reorder {s['loy_naive']:+.0%} more (naive), {s['loy_matched']:+.0%} at equal cohort, market and prior orders.</li>
<li><b>Machine opens</b> (Apple MPP) from Sep 2025: open rate {s['mpp_open_before']:.0%} -> {s['mpp_open_after']:.0%}. Subject B "won" on opens
({s['sl_open_b']:.1%} vs {s['sl_open_a']:.1%}) but lost on clicks ({s['sl_click_b']:.2%} vs {s['sl_click_a']:.2%}).</li>
<li><b>Data</b>: {s['dup_profiles']:,} duplicate DE/AT profiles; skips counted as cancellations push churn from {s['churn_true']:.1%} to {s['churn_naive']:.1%};
{s['utc_slip_share']:.1%} of subscription orders change month in UTC. Fixed in staging, tested.</li></ul>""")
    loc = card(f"""<h2>Localisation test (FR)</h2><p class="small">Welcome translated from German vs rewritten for France (beauty ritual):
revenue per recipient EUR {s['fr_rpr_adapted']:.2f} vs {s['fr_rpr_translated']:.2f} (+/- {s['fr_rpr_ci']:.2f}), unsubscribes per email
{s['fr_unsub_adapted']:.2%} vs {s['fr_unsub_translated']:.2%}. Keep the adaptation, extend the test.</p>""")
    body = f"""<div class="grid3">{card(img(ch['saves']))}{card(img(ch['price']))}{card(img(ch['loyalty_mpp']))}</div>
<div class="grid3 short">{subs}{traps}{loc}</div>"""
    return page(5, "Save subscribers with control, not discounts - and read loyalty and email data with care",
                "Skip, swap and save; a price rise and a comeback offer that loses margin; loyalty self-selection; machine opens; data issues fixed before any KPI.",
                ["SIMULATED"], body, "sql/01, 07, 09, 10 · docs/data_issues_log.md · copy/04_cancel_save.md · copy/01_welcome.md")


def p6(f, ch):
    p = f["public"]
    sc = pd.read_csv(PROC / "event_scorecard.csv")
    rows = "".join(f"<tr><td>{r.event_id}</td><td>{r.event}</td><td>{r.planted}</td><td>{r.found_by_sql}</td><td>{'yes' if r.handled_correctly else 'no'}</td></tr>"
                   for r in sc.itertuples())
    src = card(f"""<h2>Sources (all read or extracted on 2026-11-24)</h2><table class="small">
<tr><th>Source</th><th>Use</th><th>Terms</th></tr>
<tr><td>glow25.de: home, legal notice, product sitemap, /products/&lt;handle&gt;.js, article sitemaps</td><td>offer, plans, markets, content</td><td>public pages; facts only, no logo</td></tr>
<tr><td>Ashby public job board API</td><td>job posting</td><td>public API</td></tr>
<tr><td>Regulation (EU) 432/2012, Publications Office copy (EN, FR)</td><td>authorised claims</td><td>EU legal text</td></tr>
<tr><td>Eurostat isoc_ec_ibgs (updated {p['eurostat_updated'][:10]}; {p['eurostat_status_flags']} status flags)</td><td>online buying by country</td><td>CC BY 4.0</td></tr>
<tr><td>Wikimedia pageviews API (5 languages)</td><td>seasonality</td><td>CC0</td></tr>
<tr><td>UCI Online Retail II</td><td>CLV method demo</td><td>CC BY 4.0</td></tr>
<tr><td>Nager.Date; ECB EUR/GBP</td><td>holidays; GBP</td><td>public APIs</td></tr></table>
<p class="small">Collection: robots.txt respected (no cart, checkout, account, recommendations, sorting), 1 request / 3 s on Glow25 domains, cached once,
neutral User-Agent; products.json (rate-limited) and EUR-Lex (bot check) not used. No account, no newsletter sign-up, no form.</p>""")
    lim = card("""<h2>Limits</h2><ul class="facts small">
<li>All internal data is <b>simulated</b> (fictional "Brand G", seed 42): it shows the method and the decisions, not Glow25's results.</li>
<li>UCI is a UK gifts and homewares retailer with wholesale buyers: method demo, not a benchmark.</li>
<li>No Klaviyo or Recharge account; flow specs use standard vocabulary, no interface detail claimed.</li>
<li>The claims check is a filter, not legal advice. Jar duration (30 days) is an assumption from the trial-pack label.</li></ul>""")
    ev = card(f"""<h2>Planted vs found: the 8 simulated events <span class="mini mini-simulated">SIMULATED</span></h2>
<table class="small"><tr><th>#</th><th>Event</th><th>Planted</th><th>Found by the SQL</th><th>OK</th></tr>{rows}</table>""")
    ai = card(f"""<h2>AI note</h2><p class="quote">{AI_NOTE}</p>""", "auto")
    body = f'<div class="grid-1-1"><div class="stack">{src}{lim}</div><div class="stack">{ev}{ai}</div></div>'
    return page(6, "Methods, limits and AI note", "What is public, what is simulated, how each number is produced and checked, and what it cannot tell.",
                ["OVERVIEW"], body, "README · docs/assumptions.md · docs/data_issues_log.md · sql/99_tests.sql")


CSS = """
@page { size: 1600px 900px; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', Arial, sans-serif; color: #0B0B0B; background: #F2EFE9; }
.page { width: 1600px; height: 900px; padding: 30px 44px 22px; display: flex; flex-direction: column; page-break-after: always; overflow: hidden; background: #F2EFE9; }
header { display: flex; justify-content: space-between; align-items: flex-start; gap: 30px; }
h1 { font-size: 26px; margin: 0 0 6px; font-weight: 700; line-height: 1.15; max-width: 1300px; }
.sub { margin: 0; color: #52514E; font-size: 14.5px; max-width: 1300px; }
.tags { display: flex; gap: 6px; }
.tag { font-size: 12px; font-weight: 700; letter-spacing: .08em; padding: 5px 10px; border-radius: 4px; white-space: nowrap; color: #52514E; }
.tag-public { background: #E3EEFB; color: #1C5CAB; } .tag-simulated { background: #FBE9E0; color: #9A3B12; } .tag-overview { color: #52514E; border: 1px solid #D9D6CF; }
.mini { font-size: 10px; font-weight: 700; letter-spacing: .06em; padding: 2px 6px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
.mini-public { background: #E3EEFB; color: #1C5CAB; } .mini-simulated { background: #FBE9E0; color: #9A3B12; }
main { flex: 1; display: flex; flex-direction: column; gap: 12px; margin-top: 14px; min-height: 0; }
footer { display: flex; justify-content: space-between; gap: 20px; font-size: 11px; color: #898781; margin-top: 10px; }
.card { background: #FFFFFF; border: 1px solid #E1DDD4; border-radius: 8px; padding: 11px 15px; min-height: 0; overflow: hidden; }
.card h2 { font-size: 15.5px; margin: 0 0 6px; } .card p, .card li { font-size: 13px; line-height: 1.38; margin: 3px 0; color: #2B2A27; }
.card ul, .card ol { padding-left: 18px; margin: 4px 0; }
code { font-family: Consolas, monospace; font-size: 12px; background: #F2EFE9; padding: 0 3px; border-radius: 3px; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid2t { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; flex: 1.05; min-height: 0; }
.g0 { display: grid; grid-template-columns: 1fr 1.35fr; gap: 12px; flex: 1; min-height: 0; }
.grid-1-1 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.grid-2-1 { display: grid; grid-template-columns: 1.25fr 1fr; gap: 12px; flex: 1; min-height: 0; }
.short { flex: 0.62; }
figure { margin: 0; height: 100%; display: flex; flex-direction: column; }
figure img { width: 100%; flex: 1; min-height: 0; object-fit: contain; }
.tile .label { font-size: 12px; font-weight: 700; color: #52514E; letter-spacing: .03em; }
.tile .big { font-size: 36px; font-weight: 700; margin: 0; color: #0B0B0B; } .tile p { font-size: 12.5px; color: #52514E; }
.stack { display: flex; flex-direction: column; gap: 12px; min-height: 0; } .stack > .card { flex: 1; } .stack > .grid2, .stack > .grid2t { flex: 1; }
.auto { flex: 0 0 auto !important; }
.qs { list-style: none; padding-left: 0 !important; } .qs li { font-size: 14.5px !important; margin: 8px 0 !important; } .qs b { color: #2A78D6; margin-right: 8px; }
.pg { color: #898781; font-size: 12px; } .reco li { font-size: 13.5px !important; margin: 6px 0 !important; }
table { border-collapse: collapse; width: 100%; font-size: 12.5px; }
th { text-align: left; color: #52514E; font-weight: 600; border-bottom: 1px solid #E1DDD4; padding: 3px 6px; }
td { border-bottom: 1px solid #EFECE6; padding: 3px 6px; vertical-align: top; }
.small, .small li, table.small td { font-size: 12px !important; }
.facts li { margin: 4px 0 !important; }
.quote { font-style: italic; border-left: 3px solid #2A78D6; padding-left: 10px; }
"""


def build_html() -> Path:
    ch = charts.build_all()
    f = facts_mod.build()
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Glow25 retention case study</title><style>{CSS}</style></head><body>
{''.join(pg(f, ch) for pg in (p0, p1, p2, p3, p4, p5, p6))}</body></html>"""
    BUILD.mkdir(parents=True, exist_ok=True)
    out = BUILD / "report.html"
    out.write_text(html, encoding="utf-8")
    return out


def find_browser() -> str:
    for c in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", shutil.which("msedge") or "", shutil.which("chromium") or "",
              shutil.which("google-chrome") or ""]:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("Edge or Chrome is needed to print the PDF")


def print_pdf(html: Path) -> Path:
    tmp = BUILD / "_print.pdf"
    tmp.unlink(missing_ok=True)
    profile = tempfile.mkdtemp()
    subprocess.run([find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}",
                    "--allow-file-access-from-files", "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000",
                    f"--print-to-pdf={tmp}", html.as_uri()], check=True, timeout=180)
    last = -1
    for _ in range(120):  # Edge can return before its child process has written the file
        time.sleep(1)
        size = tmp.stat().st_size if tmp.exists() else -1
        if size > 0 and size == last:
            break
        last = size
    shutil.rmtree(profile, ignore_errors=True)
    reader, writer = PdfReader(str(tmp)), PdfWriter()
    for pg in reader.pages:
        writer.add_page(pg)
    writer.add_metadata({"/Title": "Glow25 - retention case study", "/Author": "", "/Creator": "", "/Producer": ""})
    PDF.parent.mkdir(parents=True, exist_ok=True)
    with open(PDF, "wb") as fh:
        writer.write(fh)
    tmp.unlink()
    return PDF


if __name__ == "__main__":
    pdf = print_pdf(build_html())
    print(f"written {pdf.relative_to(ROOT).as_posix()} ({len(PdfReader(str(pdf)).pages)} pages)")
