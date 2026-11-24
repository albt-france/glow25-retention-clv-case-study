"""Claims guardrail for email copy (English and French). Not legal advice: a first filter before human review.

Rules (docs/claims_guardrail.md):
  BLOCK  a banned word or phrase (cure, anti-ageing, before/after, ...), in English or French;
  BLOCK  a sentence that links a body function (skin, hair, joints, bones, energy, ...) to an effect
         ("supports", "improves", "contribue", ...) and is not one of the authorised wordings of
         Regulation (EU) No 432/2012 that mention collagen (vitamin C only; read from data/public/);
  BLOCK  "clinically proven" / "studies show" without a source marker [source: ...];
  PASS   everything else - and a human still reads every email before it is scheduled.

Mentions, not claims: text inside `backticks` and lines containing "claims-check: ignore" are skipped, so
documentation can list banned words.

    python src/claims_check.py copy/            (files or folders; .md and .txt)
    python src/claims_check.py copy/ docs/
Exit code 1 if anything is blocked. Report: data/processed/claims_check_report.csv
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

BANNED = [
    # English
    r"anti[- ]?ag(e)?ing", r"\bheal(s|ing|ed)?\b", r"\bcure(s|d)?\b", r"\btreat(s|ment|ments)?\b", r"wrinkles? (disappear|vanish|gone)",
    r"\breverse(s|d)?\b", r"younger[- ]looking", r"look(s)? years younger", r"\bdetox", r"\bmiracle", r"guaranteed results?",
    r"before[- /]and[- /]after", r"before\s*/\s*after", r"\bprevents?\b", r"\brejuvenat", r"medical(ly)?", r"doctor[- ]recommended",
    # French
    r"anti[- ]?(â|a)ge", r"anti[- ]?rides", r"gu(é|e)ri(t|r|son)", r"\bsoign(e|er|ant)", r"\btrait(e|er|ement)\b", r"rajeuni",
    r"avant\s*/\s*apr(è|e)s", r"avant[- ]apr(è|e)s", r"les rides (disparaissent|s'effacent)", r"\bpr(é|e)vien", r"miracle",
]
UNSOURCED = [r"clinically (proven|tested|shown)", r"studies show", r"scientifically proven", r"cliniquement (prouv|test|d(é|e)montr)",
             r"(é|e)tudes? (montrent|prouvent)", r"scientifiquement prouv"]
BODY = [r"\bskin\b", r"\bhair\b", r"\bnails?\b", r"\bjoints?\b", r"\bbones?\b", r"\bcartilage", r"\bgums?\b", r"\bteeth\b",
        r"blood vessels?", r"\bimmun", r"\benergy\b", r"\btiredness\b", r"\bfatigue\b", r"collagen formation", r"\belasticity\b",
        r"\bwrinkles?\b", r"\bmetabolism\b", r"\bmuscles?\b",
        r"\bpeau\b", r"\bcheveux\b", r"\bongles?\b", r"\barticulations?\b", r"\bos\b", r"\bcartilages?\b", r"\bgencives?\b",
        r"\bdents\b", r"vaisseaux sanguins", r"\bimmunit", r"\b(é|e)nergie\b", r"\bfatigue\b", r"formation (normale )?de collag(è|e)ne",
        r"(é|e)lasticit(é|e)", r"\brides\b"]
EFFECT = [r"contribut", r"\bsupport", r"\bimprov", r"\bboost", r"\breduc", r"\bhelp", r"\bpromot", r"\bstrengthen", r"\bfor (the )?(healthy|normal)\b", r"pour assurer",
          r"\bmaintain", r"\bfirm(er|s)?\b", r"\bplump", r"\bsmooth(er|s)?\b", r"\brepair", r"\bfight", r"\bnourish",
          r"contribue", r"\bam(é|e)liore", r"\baide\b", r"\baident\b", r"\bfavorise", r"\brenforce", r"\br(é|e)duit", r"\braffermi",
          r"\blisse", r"\bentretien", r"\bpour (une|des|la|le) .* (normale?s?|saine?s?)"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s).replace("’", "'").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def whitelist() -> list[str]:
    w = pd.read_csv(ROOT / "data" / "public" / "eu_432_2012_collagen_claims.csv")
    return [norm(x).rstrip(".") for x in w.authorised_claim]


def blocks(text: str):
    """Paragraphs and list items joined across line breaks (a claim split over two lines is still one sentence)."""
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    cur, start = [], 1
    for i, line in enumerate(text.splitlines() + [""], 1):
        new_item = not line.strip() or re.match(r"\s*([-*+]|\d+[.)]|#|\||\*\*\[)", line)
        if new_item and cur:
            yield start, " ".join(cur)
            cur = []
        if line.strip():
            if not cur:
                start = i
            cur.append(line.strip())


def sentences(text: str):
    for i, block in blocks(text):
        if "claims-check: ignore" in block:
            continue
        block = re.sub(r"`[^`]*`", " ", block)                 # mentions in backticks are not claims
        block = re.sub(r"\[source:[^\]]*\]", " [source] ", block)
        for s in re.split(r"(?<=[.!?])\s+", block):
            if s.strip():
                yield i, s.strip()


def check_text(text: str, wl: list[str]):
    out = []
    for ln, s in sentences(text):
        n = norm(s)
        n_wo = n
        for w in wl:                                           # remove authorised wordings before looking for claims
            n_wo = n_wo.replace(w, " ")
        banned = [p for p in BANNED if re.search(p, n_wo)]
        unsourced = [p for p in UNSOURCED if re.search(p, n_wo) and "[source]" not in n_wo]
        body = [p for p in BODY if re.search(p, n_wo)]
        effect = [p for p in EFFECT if re.search(p, n_wo)]
        if banned:
            out.append((ln, "BLOCK", "banned wording", s))
        elif unsourced:
            out.append((ln, "BLOCK", "evidence claim without a source", s))
        elif body and effect:
            out.append((ln, "BLOCK", "health claim not in the authorised list (EU 432/2012)", s))
        elif n != n_wo:
            out.append((ln, "PASS", "authorised claim, verbatim (check the product contains vitamin C at a significant level)", s))
    return out


def run(paths: list[str]) -> int:
    wl = whitelist()
    files = []
    for p in paths:
        p = Path(p)
        files += sorted(p.rglob("*.md")) + sorted(p.rglob("*.txt")) if p.is_dir() else [p]
    rows = []
    for f in files:
        for ln, status, why, s in check_text(f.read_text(encoding="utf-8"), wl):
            rows.append({"file": f.resolve().relative_to(ROOT).as_posix(), "line": ln, "status": status, "rule": why, "sentence": s[:200]})
    rep = pd.DataFrame(rows, columns=["file", "line", "status", "rule", "sentence"])
    out = ROOT / "data" / "processed" / "claims_check_report.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rep.to_csv(out, index=False)
    blocked = rep[rep.status == "BLOCK"]
    print(f"{len(files)} files checked: {len(blocked)} blocked, {int((rep.status == 'PASS').sum())} authorised claims found.")
    for r in blocked.itertuples():
        print(f"  BLOCK {r.file}:{r.line} [{r.rule}] {r.sentence[:110]}")
    print("Human review is still required for every email: claims, tone, offer, legal sign-off (this is not legal advice).")
    return 1 if len(blocked) else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:] or ["copy"]))
