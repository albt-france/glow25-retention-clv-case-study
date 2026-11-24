"""Copy lab: customer research on SIMULATED cancel reasons -> brief -> subject-line variants -> claims check.

Default (used in this repository): rule-based themes and template variants, no key needed.
Optional: a language-model step (src/llm_client.py) proposes extra variants when .env sets LLM_PROVIDER and
LLM_API_KEY. Every variant, whatever its origin, goes through src/claims_check.py; a person makes the final call.

    python src/copy_lab.py   -> data/processed/copy_lab_themes.csv, data/processed/copy_lab_variants.csv
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

import claims_check
import llm_client

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"
THEMES = {  # cancel reason -> theme, insight, action (written by a person)
    "have_too_much": ("Too much product at home", "Customers stockpile when deliveries outrun use", "skip a delivery"),
    "too_expensive": ("Price", "The price, not the product, is the issue", "change the delivery rhythm"),
    "not_for_me": ("Taste or format", "The format does not fit the morning", "swap flavour or format"),
    "switching_brand": ("Competitor", "Customer compares offers", "remind what the subscription includes"),
    "other": ("Other", "Mixed reasons", "pause for up to 3 months"),
    "payment_failed": ("Payment failed", "Involuntary churn, not a decision", "update payment details"),
}
TEMPLATES = [
    "Before you go: {action} instead?",
    "Your subscription, your rhythm: {action}",
    "One click to {action}",
    "Not cancelling, just {action}?",
    "{theme}? You can {action} today",
    "We kept it simple: {action} in two clicks",
]


def themes() -> pd.DataFrame:
    con = duckdb.connect()
    s = con.execute(f"select cancel_reason, count(*) as n from read_parquet('{(ROOT / 'data/sim/subscriptions.parquet').as_posix()}') "
                    "where cancel_reason is not null group by 1 order by 2 desc").df()
    s["theme"] = s.cancel_reason.map(lambda r: THEMES[r][0])
    s["insight"] = s.cancel_reason.map(lambda r: THEMES[r][1])
    s["action"] = s.cancel_reason.map(lambda r: THEMES[r][2])
    s["share"] = s.n / s.n.sum()
    s["data"] = "SIMULATED (Brand G)"
    return s


def variants(th: pd.DataFrame) -> pd.DataFrame:
    wl = claims_check.whitelist()
    rows = []
    for r in th[th.cancel_reason != "payment_failed"].itertuples():
        brief = {"theme": r.theme, "insight": r.insight, "action": r.action, "product": "collagen powder subscription"}
        cands = [(t.format(theme=r.theme, action=r.action), "template") for t in TEMPLATES]
        llm = llm_client.subject_lines(brief) if llm_client.available() else None
        cands += [(c, "language-model step (optional)") for c in (llm or [])]
        for text, origin in cands:
            res = claims_check.check_text(text, wl)
            blocked = any(s == "BLOCK" for _, s, _, _ in res)
            rows.append({"cancel_reason": r.cancel_reason, "theme": r.theme, "subject_line": text, "origin": origin,
                         "claims_check": "BLOCK" if blocked else "PASS", "human_validated": False})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    th = themes()
    th.to_csv(OUT / "copy_lab_themes.csv", index=False)
    v = variants(th)
    v.to_csv(OUT / "copy_lab_variants.csv", index=False)
    print(f"{len(th)} themes; {len(v)} variants ({(v.origin != 'template').sum()} from the language-model step); "
          f"{(v.claims_check == 'BLOCK').sum()} blocked by the claims check. human_validated = False until a person signs off.")
