"""Retention economics workbook (real Excel formulas; blue cells are inputs you can change).

Tabs: Order_Margin, Subscription_Scenarios, Flow_Holdout, Sample_Size, Checks. Inputs are read from the SQL
outputs (SIMULATED Brand G data) and written as values; every result is a formula. File metadata left empty.

    python src/build_excel.py   -> excel/retention_economics.xlsx
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "excel" / "retention_economics.xlsx"
BLUE = Font(color="1F4FD1")
BOLD = Font(bold=True)
TITLE = Font(bold=True, size=14)
NOTE = Font(italic=True, color="6B6A65", size=9)
INPUT_FILL = PatternFill("solid", fgColor="EAF1FC")
HEAD_FILL = PatternFill("solid", fgColor="F2EFE9")
THIN = Border(bottom=Side(style="thin", color="D9D6CF"))
EUR, PCT, INT, DEC = '#,##0.00 "EUR"', "0.0%", "#,##0", "0.000"
TAG = "SIMULATED data (fictional Brand G) - not Glow25's numbers. Blue = input, black = formula."


def csv(n):
    return pd.read_csv(PROC / f"{n}.csv")


def header(ws, title, sub, widths):
    ws["A1"], ws["A1"].font = title, TITLE
    ws["A2"], ws["A2"].font = sub, NOTE
    ws["A3"], ws["A3"].font = TAG, NOTE
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def inp(c, v, fmt=None):
    c.value, c.font, c.fill = v, BLUE, INPUT_FILL
    if fmt:
        c.number_format = fmt


def fml(c, f, fmt=None, bold=False):
    c.value = f
    if fmt:
        c.number_format = fmt
    if bold:
        c.font = BOLD


def head_row(ws, r, labels):
    for j, lab in enumerate(labels, 1):
        c = ws.cell(r, j, lab)
        c.font, c.fill, c.border = BOLD, HEAD_FILL, THIN
        c.alignment = Alignment(wrap_text=True, vertical="top")


# ------------------------------------------------------------------ 1. Order margin
def order_margin(wb):
    ws = wb.active
    ws.title = "Order_Margin"
    header(ws, "Contribution margin per order", "CM = gross - discount - cost of goods - shipping - payment fees - refunds "
           "(net of VAT). Prices and plan discounts are Glow25's public ones; costs are assumptions.", [34, 16, 16, 16, 16, 16])
    cols = ["One-off jar", "Monthly sub (-15%)", "Every 3 months (-25%, 3 jars)", "Win-back -30% charge", "Trial pack 225 g"]
    head_row(ws, 5, ["Line"] + cols)
    inputs = [("List price per unit (EUR)", [29.99, 37.38, 37.24, 29.99, 14.99], EUR),
              ("Units per order", [1, 1, 3, 1, 1], INT),
              ("Discount rate", [0, 0.15, 0.25, 0.30, 0], PCT),
              ("Cost of goods per unit (EUR)", [6.90, 8.09, 8.07, 6.90, 3.60], EUR),
              ("Shipping cost per parcel (EUR)", [4.20, 5.38, 9.40, 4.20, 4.20], EUR),
              ("Payment fee, % of net", [0.019] * 5, PCT),
              ("Payment fee, fixed (EUR)", [0.25] * 5, EUR),
              ("Refund rate (share of net refunded)", [0.025, 0.01, 0.01, 0.01, 0.025], PCT)]
    for i, (lab, vals, fmt) in enumerate(inputs, 6):
        ws.cell(i, 1, lab)
        for j, v in enumerate(vals, 2):
            inp(ws.cell(i, j), v, fmt)
    lines = [("Gross (EUR)", "={c}6*{c}7"), ("Discount (EUR)", "={c}15*{c}8"), ("Net revenue (EUR)", "={c}15-{c}16"),
             ("Cost of goods (EUR)", "={c}9*{c}7"), ("Shipping (EUR)", "={c}10"), ("Payment fees (EUR)", "={c}17*{c}11+{c}12"),
             ("Refunds (EUR)", "={c}17*{c}13"), ("Contribution margin (EUR)", "={c}17-{c}18-{c}19-{c}20-{c}21"),
             ("CM % of net revenue", "=IF({c}17=0,0,{c}22/{c}17)"), ("CM per jar (EUR)", "={c}22/{c}7")]
    for i, (lab, f) in enumerate(lines, 15):
        ws.cell(i, 1, lab).font = BOLD if i in (22, 24) else Font()
        for j in range(2, 7):
            c = get_column_letter(j)
            fml(ws.cell(i, j), f.format(c=c), PCT if i == 23 else EUR, bold=i in (22, 24))
    ws["A26"] = "Reading: the every-3-months plan earns more per order, but less per jar (deeper discount, heavier parcel)."
    ws["A26"].font = NOTE
    ws["A27"] = ("One-off and win-back columns use Glow25's public jar price (EUR 29.99). Subscription columns use the average "
                 "list price, cost and shipping of the SIMULATED subscription mix (Plus, Intensiv, swaps, +10 % from April 2026).")
    ws["A27"].font = NOTE


# ------------------------------------------------------------------ 2. Subscription scenarios
def subscription(wb):
    ws = wb.create_sheet("Subscription_Scenarios")
    header(ws, "Monthly -15 % vs every 3 months -25 %: retention vs margin (12 months)",
           "Survival curves, skip and add-on rates come from 07_subscription_economics.sql (subscriptions started Nov 2024 - Oct 2025).",
           [30, 14, 14, 4, 34, 16, 16])
    curve = csv("sub_retention_curve").pivot(index="day", columns="interval", values="still_active")
    sp = csv("sub_plan_economics").set_index("interval")
    head_row(ws, 5, ["Day since start", "Monthly: still active", "3-monthly: still active"])
    for i, (day, r) in enumerate(curve.iterrows(), 6):
        ws.cell(i, 1, int(day))
        inp(ws.cell(i, 2), round(float(r["1M"]), 4), PCT)
        inp(ws.cell(i, 3), round(float(r["3M"]), 4), PCT)
    last = 5 + len(curve)                                   # rows 6..19 for days 0..390
    head_row(ws, 5, ["Day since start", "Monthly: still active", "3-monthly: still active", "", "Assumption / result", "Monthly", "Every 3 months"])
    rows = [
        ("Skip rate per scheduled charge", sp.loc["1M", "skip_rate_per_scheduled_charge"], sp.loc["3M", "skip_rate_per_scheduled_charge"], PCT, True),
        ("Add-on rate per paid charge", 0.17, 0.03, PCT, True),
        ("CM of an add-on item (EUR)", 30.0, 30.0, EUR, True),
        ("CM per paid charge, reference jar (from Order_Margin)", "=Order_Margin!C22", "=Order_Margin!D22", EUR, False),
        ("Scheduled charges in 365 days (days 0-360)", 13, 5, INT, True),
        ("Expected paid charges in 12 months", None, None, DEC, False),
        ("CM-CLV 12 months, model (EUR)", None, None, EUR, False),
        ("Retention at 12 months (day 360)", None, None, PCT, False),
        ("CM-CLV 12 months, observed in SQL (EUR)", sp.loc["1M", "cm_clv_12m_eur"], sp.loc["3M", "cm_clv_12m_eur"], EUR, True),
        ("Retention 12 months, observed in SQL", sp.loc["1M", "retention_12m"], sp.loc["3M", "retention_12m"], PCT, True),
        ("Quarterly vs monthly, model", None, None, PCT, False),
        ("Quarterly vs monthly, observed", None, None, PCT, False),
    ]
    r0 = 6
    for k, (lab, m, q, fmt, is_inp) in enumerate(rows):
        r = r0 + k
        ws.cell(r, 5, lab)
        for col, v in ((6, m), (7, q)):
            if v is None:
                continue
            (inp if is_inp else fml)(ws.cell(r, col), round(v, 4) if isinstance(v, float) else v, fmt)
    # rows: 6 skip, 7 addon rate, 8 addon cm, 9 cm/charge, 10 scheduled, 11 paid, 12 cmclv, 13 retention, 14 obs cmclv, 15 obs ret, 16, 17
    # monthly charges on days 0,30,...,360 -> curve rows 6..18; first charge is never skipped
    fml(ws["F11"], "=B6+SUM(B7:B18)*(1-F6)", DEC)
    # every-3-months charges on days 0, 90, 180, 270, 360 -> rows 6, 9, 12, 15, 18
    fml(ws["G11"], "=C6+(C9+C12+C15+C18)*(1-G6)", DEC)
    fml(ws["F12"], "=F11*(F9+F7*F8)", EUR, bold=True)
    fml(ws["G12"], "=G11*(G9+G7*G8)", EUR, bold=True)
    fml(ws["F13"], f"=B{6 + 12}", PCT)
    fml(ws["G13"], f"=C{6 + 12}", PCT)
    fml(ws["F16"], "=G12/F12-1", PCT, bold=True)
    fml(ws["F17"], "=G14/F14-1", PCT, bold=True)
    steps = [
        "Step-by-step reasoning (read before the conclusion):",
        "1. Retention: the every-3-months plan keeps more subscribers at 12 months (row 13 / 15).",
        "2. But each jar earns less: -25 % instead of -15 %, and the 3-jar parcel costs more to ship (Order_Margin row 24).",
        "3. Subscribers on 3-month deliveries skip more often (stock builds up at home) and buy fewer add-ons (rows 6-7).",
        "4. Paid charges x CM per charge = CM-CLV: the monthly plan ends higher despite lower retention (rows 12, 16, 17).",
        "5. Decision: keep both plans, show the monthly plan first with skip / swap / pause, do not deepen the discount.",
        "Change the blue cells (discount in Order_Margin, skip rate, add-on rate) to see when the 3-month plan would win.",
    ]
    for i, s in enumerate(steps, 21):
        ws.cell(i, 5, s).font = BOLD if i == 21 else Font()


# ------------------------------------------------------------------ 3. Flow holdout
def flow_holdout(wb, arms):
    ws = wb.create_sheet("Flow_Holdout")
    header(ws, "Attributed vs incremental revenue per flow (10 % holdout)",
           "Incremental = (revenue per treated entrant - revenue per holdout entrant) x treated entrants, over the flow window.",
           [26, 9, 11, 11, 11, 11, 11, 11, 12, 12, 12, 14, 14, 12, 12, 12])
    cols = ["Flow", "Window (d)", "Treated n", "Holdout n", "Rev / treated", "Rev / holdout", "SD treated", "SD holdout",
            "Difference", "95 % CI low", "95 % CI high", "Incremental EUR", "Attributed EUR", "Incremental share", "Share CI low", "Share CI high"]
    head_row(ws, 5, cols)
    fr = csv("flow_holdout_readout").set_index("flow")
    order = ["F2_education", "F4_replenishment", "F3_trial_to_sub", "F6_cancel_save", "F7_winback", "F1_welcome", "F5_sub_onboarding",
             "F8_vip_loyalty", "VIP early access (Gold)"]
    for i, f in enumerate(order, 6):
        a = arms.loc[f]
        ws.cell(i, 1, f)
        ws.cell(i, 2, int(fr.loc[f, "window_days"]))
        for col, v, fmt in ((3, a.n_t, INT), (4, a.n_h, INT), (5, a.rpr_t, EUR), (6, a.rpr_h, EUR), (7, a.sd_t, EUR), (8, a.sd_h, EUR)):
            inp(ws.cell(i, col), float(v), fmt)
        att = fr.loc[f, "attributed_revenue_eur"]
        inp(ws.cell(i, 13), round(float(att), 2) if pd.notna(att) else 0, EUR)
        fml(ws.cell(i, 9), f"=E{i}-F{i}", EUR)
        fml(ws.cell(i, 10), f"=I{i}-_xlfn.NORM.S.INV(0.975)*SQRT(G{i}^2/C{i}+H{i}^2/D{i})", EUR)
        fml(ws.cell(i, 11), f"=I{i}+_xlfn.NORM.S.INV(0.975)*SQRT(G{i}^2/C{i}+H{i}^2/D{i})", EUR)
        fml(ws.cell(i, 12), f"=I{i}*C{i}", EUR, bold=True)
        fml(ws.cell(i, 14), f'=IF(M{i}>0,L{i}/M{i},"n/a")', PCT, bold=True)
        fml(ws.cell(i, 15), f'=IF(M{i}>0,J{i}*C{i}/M{i},"n/a")', PCT)
        fml(ws.cell(i, 16), f'=IF(M{i}>0,K{i}*C{i}/M{i},"n/a")', PCT)
    n = 5 + len(order)
    ws.cell(n + 2, 1, "Reading: the education flow claims the most revenue, but most of it would have happened anyway; "
                      "replenishment is mostly incremental. Cancel-save and onboarding are judged on churn, not on attributed revenue.").font = NOTE


# ------------------------------------------------------------------ 4. Sample size
def sample_size(wb):
    ws = wb.create_sheet("Sample_Size")
    header(ws, "Holdout size and minimum detectable effect (MDE)", "Two-sided test, normal approximation. Change the blue cells.",
           [52, 16, 4, 52, 16])
    head_row(ws, 5, ["Revenue per recipient (mean)", "Value", "", "Repurchase rate (proportion), A/B 50/50", "Value"])
    left = [("Baseline revenue per recipient (EUR)", 12.89, EUR, True), ("Standard deviation per recipient (EUR)", 20.9, EUR, True),
            ("Holdout share", 0.10, PCT, True), ("Entrants per month", 6500, INT, True), ("Significance (alpha)", 0.05, PCT, True),
            ("Power", 0.80, PCT, True), ("Target relative MDE", 0.05, PCT, True),
            ("z (1 - alpha/2) + z (power)", "=_xlfn.NORM.S.INV(1-B10/2)+_xlfn.NORM.S.INV(B11)", DEC, False),
            ("Entrants needed (total)", "=B13^2*B7^2*(1/B8+1/(1-B8))/(B12*B6)^2", INT, False),
            ("Months needed", "=B14/B9", DEC, False),
            ("MDE with 12 months of entrants (EUR)", "=B13*B7*SQRT(1/(B9*12*B8)+1/(B9*12*(1-B8)))", EUR, False),
            ("MDE with 12 months, relative", "=B16/B6", PCT, False)]
    for i, (lab, v, fmt, is_inp) in enumerate(left, 6):
        ws.cell(i, 1, lab)
        (inp if is_inp else fml)(ws.cell(i, 2), v, fmt)
    right = [("Baseline 60-day repurchase", 0.515, PCT, True), ("MDE (absolute, points)", 0.03, PCT, True),
             ("Significance (alpha)", 0.05, PCT, True), ("Power", 0.80, PCT, True),
             ("n per arm", "=(_xlfn.NORM.S.INV(1-E8/2)+_xlfn.NORM.S.INV(E9))^2*(E6*(1-E6)+(E6+E7)*(1-E6-E7))/E7^2", INT, False),
             ("Triggers per month (all arms)", 6000, INT, True), ("Months needed (2 arms)", "=2*E10/E11", DEC, False)]
    for i, (lab, v, fmt, is_inp) in enumerate(right, 6):
        ws.cell(i, 4, lab)
        (inp if is_inp else fml)(ws.cell(i, 5), v, fmt)
    ws["A19"] = "Rule: decide only when the planned sample is reached and one full purchase cycle (35 days) has passed. Never on open rate."
    ws["A19"].font = NOTE


# ------------------------------------------------------------------ 5. Checks
def checks(wb, arms):
    ws = wb.create_sheet("Checks")
    header(ws, "Checks: workbook formulas vs SQL outputs", "OK if the difference is within the tolerance.", [60, 18, 18, 12, 10])
    head_row(ws, 5, ["Check", "Workbook (formula)", "SQL output", "Tolerance", "Status"])
    fr = csv("flow_holdout_readout").set_index("flow")
    wf = csv("cm_waterfall").set_index("step").eur
    om = csv("cm_by_order_type")
    tot = om[om.order_type.isna()].iloc[0]
    sp = csv("sub_plan_economics").set_index("interval")
    rows = [
        ("Education: incremental revenue (EUR)", "=Flow_Holdout!L6", fr.loc["F2_education", "incremental_revenue_eur"], 2.0),
        ("Replenishment: incremental revenue (EUR)", "=Flow_Holdout!L7", fr.loc["F4_replenishment", "incremental_revenue_eur"], 2.0),
        ("Education: incremental share of attributed", "=Flow_Holdout!N6", fr.loc["F2_education", "incremental_share_of_attributed"], 0.001),
        ("Education: 95 % CI half-width x n (EUR)", "=(Flow_Holdout!K6-Flow_Holdout!I6)*Flow_Holdout!C6", fr.loc["F2_education", "incremental_revenue_ci95"], 2.0),
        ("CM waterfall: gross - all costs = CM (EUR)", f"={wf['gross']}{wf['discounts']:+}{wf['cost of goods']:+}{wf['shipping']:+}{wf['payment fees']:+}{wf['refunds']:+}",
         wf["contribution margin"], 1.0),
        ("Average CM per order x orders = total CM (EUR)", f"={tot.cm_per_order}*{int(tot.orders)}", tot.cm_total_eur, 5.0),
        ("Monthly plan: model CM-CLV 12 m within 15 % of SQL", "=Subscription_Scenarios!F12/Subscription_Scenarios!F14-1", 0.0, 0.15),
        ("3-monthly plan: model CM-CLV 12 m within 15 % of SQL", "=Subscription_Scenarios!G12/Subscription_Scenarios!G14-1", 0.0, 0.15),
        ("Model and SQL agree on the sign (3-monthly below monthly)", "=SIGN(Subscription_Scenarios!F16)", float(1 if sp.loc["3M", "cm_clv_12m_eur"] > sp.loc["1M", "cm_clv_12m_eur"] else -1), 0.0),
        ("Holdout share, education flow", "=Flow_Holdout!D6/(Flow_Holdout!C6+Flow_Holdout!D6)", 0.10, 0.005),
    ]
    for i, (lab, f, sql, tol) in enumerate(rows, 6):
        ws.cell(i, 1, lab)
        fml(ws.cell(i, 2), f, "0.0000")
        inp(ws.cell(i, 3), round(float(sql), 6), "0.0000")
        inp(ws.cell(i, 4), tol)
        fml(ws.cell(i, 5), f'=IF(ABS(B{i}-C{i})<=D{i},"OK","MISMATCH")', bold=True)
    n = 5 + len(rows)
    ws.cell(n + 2, 1, "All checks")
    fml(ws.cell(n + 2, 5), f'=IF(COUNTIF(E6:E{n},"OK")={len(rows)},"OK","MISMATCH")', bold=True)


def main():
    con = duckdb.connect(str(ROOT / "data" / "sim" / "retention.duckdb"), read_only=True)
    arms = con.execute("""
        select flow, count(*) filter (where not holdout) as n_t, count(*) filter (where holdout) as n_h,
               avg(revenue_eur) filter (where not holdout) as rpr_t, avg(revenue_eur) filter (where holdout) as rpr_h,
               stddev_samp(revenue_eur) filter (where not holdout) as sd_t, stddev_samp(revenue_eur) filter (where holdout) as sd_h
        from flow_outcome group by flow""").df().set_index("flow")
    wb = Workbook()
    order_margin(wb)
    subscription(wb)
    flow_holdout(wb, arms)
    sample_size(wb)
    checks(wb, arms)
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.freeze_panes = "A6"
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    p = wb.properties
    p.creator, p.lastModifiedBy, p.title, p.subject, p.description, p.keywords, p.category = "", "", "", "", "", "", ""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"written {OUT.relative_to(ROOT).as_posix()} ({len(wb.sheetnames)} tabs: {', '.join(wb.sheetnames)})")


if __name__ == "__main__":
    main()
