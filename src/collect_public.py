"""Collect every public input once (cached in data/raw/, which is never published) and write tidy files to
data/public/. Re-running reads the cache: glow25.de is contacted at most once per URL.

Sources (all public, no account, no form, no key):
  1. Ashby public job board API (the job posting)
  2. glow25.de: home page (hreflang markets, app blocks), product sitemap, /products/<handle>.js, article sitemap
  3. Regulation (EU) No 432/2012 (Publications Office copy; EUR-Lex itself is not used)
  4. Eurostat isoc_ec_ibgs (JSON-stat)
  5. Wikimedia pageviews (monthly, user agents)
  6. UCI Online Retail II (CC BY 4.0) -> invoice-level, customer ids only
  7. Nager.Date public holidays, ECB EUR/GBP reference rate

    python src/collect_public.py
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import quote

import pandas as pd

import polite

ROOT = Path(__file__).resolve().parents[1]
RAW, PUB = ROOT / "data" / "raw", ROOT / "data" / "public"
EXTRACTED = "2026-11-24"
SHOP = "https://glow25.de"
# One bundle handle carries a person's name. It is matched by the first 12 hex characters of its SHA-256 and renamed
# celebrity-routine-bundle (title "Celebrity routine bundle"), so the name is never written anywhere.
PERSON_HANDLE_HASHES = {"7bcb25aef38f"}


def h12(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def save(df: pd.DataFrame, name: str) -> None:
    df.to_csv(PUB / f"{name}.csv", index=False)
    print(f"  data/public/{name}.csv ({len(df)} rows)")


# ------------------------------------------------------------------ 1. job posting
def ashby():
    _, body = polite.get("https://api.ashbyhq.com/posting-api/job-board/glow25?includeCompensation=true")
    jobs = json.loads(body)["jobs"]
    rows = [{"title": j["title"], "department": j.get("department"), "location": j.get("location"),
             "employment_type": j.get("employmentType"), "is_remote": j.get("isRemote"),
             "published_at": j.get("publishedAt", "")[:16],
             "compensation_tiers": len((j.get("compensation") or {}).get("compensationTiers") or []),
             "address_country": ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry")}
            for j in jobs]
    save(pd.DataFrame(rows), "job_board")


# ------------------------------------------------------------------ 2. shop
def shop_home():
    _, html = polite.get(f"{SHOP}/de-de")
    langs = sorted(set(re.findall(r'hreflang="([a-z]{2}-[A-Z]{2})"', html)))
    stack = {"shopify": "myshopify.com" in html or "Shopify." in html,
             "klaviyo": "klaviyo" in html.lower(), "recharge": "recharge" in html.lower()}
    shop_domain = (re.findall(r"([a-z0-9-]+\.myshopify\.com)", html) or [""])[0]
    rows = [{"hreflang": l, "language": l[:2], "market": l[3:]} for l in langs]
    save(pd.DataFrame(rows), "shop_markets")
    save(pd.DataFrame([{"signal": k, "visible_in_public_html": v} for k, v in stack.items()]
                      + [{"signal": "shop_domain", "visible_in_public_html": shop_domain}]), "shop_stack")


def dose_and_content(desc: str):
    """Grams per pack and grams per daily serving when the description states them; else None."""
    t = re.sub(r"<[^>]+>", " ", desc or "").replace("\xa0", " ")
    pack = re.findall(r"(\d{2,4})\s?g\b(?!\s*(?:Kollagen|Protein|pro|je|/))", t)
    serving = re.findall(r"(\d{1,2}(?:[.,]\d)?)\s?g\s*(?:\(|pro Tag|täglich|pro Portion|je Portion|=|Kollagen)", t)
    portions = re.findall(r"(\d{2,3})\s*(?:Portionen|Tagesportionen|Anwendungen|Tage)", t)
    return (max(map(int, pack)) if pack else None,
            float(serving[0].replace(",", ".")) if serving else None,
            int(portions[0]) if portions else None)


def catalogue():
    _, xml = polite.get(f"{SHOP}/de-de/sitemap_products_1.xml?from=15569419600197&to=16407699226949")
    handles = [h for h in re.findall(r"/products/([a-z0-9\-]+)</loc>", xml)]
    rows, plans = [], []
    for handle in handles:
        st, body = polite.get(f"{SHOP}/de-de/products/{handle}.js")
        if st != 200 or not body:
            continue
        p = json.loads(body)
        person = h12(handle) in PERSON_HANDLE_HASHES
        safe_handle = "celebrity-routine-bundle" if person else handle
        title = "Celebrity routine bundle" if person else p["title"]
        grams, serving, portions = dose_and_content(p.get("description", ""))
        groups = p.get("selling_plan_groups") or []
        for g in groups:
            for sp in g.get("selling_plans", []):
                adj = (sp.get("price_adjustments") or [{}])[0]
                plans.append({"handle": safe_handle, "app_id": g.get("app_id"), "plan_name": sp.get("name"),
                              "adjustment_type": adj.get("value_type"), "adjustment_value": adj.get("value")})
        rows.append({"handle": safe_handle, "title": title, "type": p.get("type"),
                     "price_eur": p["price"] / 100, "n_variants": len(p.get("variants", [])),
                     "available": p.get("available"), "subscribable": bool(groups),
                     "requires_selling_plan": p.get("requires_selling_plan"),
                     "variant_weight_g": (p.get("variants") or [{}])[0].get("weight"), "pack_grams": grams, "serving_grams": serving, "portions_stated": portions,
                     "created_at": (p.get("created_at") or "")[:10]})
    cat = pd.DataFrame(rows)
    save(cat, "glow25_catalogue")
    save(pd.DataFrame(plans), "glow25_selling_plans")


def articles():
    """Blog articles per country domain (hreflang targets), read from each domain's article sitemap."""
    rows = []
    for domain, sitemaps in {"glow25.de": ["sitemap_articles_1.xml", "en-de/sitemap_articles_1.xml"],
                             "glow25.fr": ["sitemap_articles_1.xml"], "glow25.it": ["sitemap_articles_1.xml"],
                             "glow25.nl": ["sitemap_articles_1.xml"], "glow25.es": ["sitemap_articles_1.xml"],
                             "glow25.co.uk": ["sitemap_articles_1.xml"]}.items():
        for sm in sitemaps:
            st, xml = polite.get(f"https://{domain}/{sm}")
            locs = re.findall(r"<loc>([^<]+/blogs/[^<]+)</loc>", xml or "") if st == 200 else []
            rows.append({"domain": domain, "sitemap": sm, "http_status": st, "articles": len(locs)})
    save(pd.DataFrame(rows), "glow25_articles_by_domain")


# ------------------------------------------------------------------ 3. regulation 432/2012
def regulation():
    """Authorised claims that mention collagen: English and French official versions (Publications Office copy)."""
    rows = []
    for lang, start, word in (("EN", "Vitamin C", "collagen"), ("FR", "La vitamine C", "collagène")):
        st, html = polite.get(f"https://publications.europa.eu/resource/celex/32012R0432.{'ENG' if lang == 'EN' else 'FRA'}.xhtml",
                              headers={"Accept": "application/xhtml+xml"})
        text = re.sub(r"<[^>]+>", "\n", html)
        lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
        claims = sorted({l for l in lines if word in l and l.startswith(start)})
        other = sum(word in l.lower() and not l.startswith(start) and len(l) > 30 for l in lines)
        print(f"  {lang}: {len(claims)} authorised claims mention {word}; other long lines mentioning it: {other}")
        rows += [{"language": lang, "authorised_claim": c, "nutrient": "Vitamin C"} for c in claims]
    df = pd.DataFrame(rows)
    df["source"], df["extracted"] = "Regulation (EU) No 432/2012, Annex (Publications Office copy)", EXTRACTED
    save(df, "eu_432_2012_collagen_claims")


# ------------------------------------------------------------------ 4. Eurostat
def eurostat():
    geos = "&".join(f"geo={g}" for g in ["DE", "FR", "IT", "ES", "NL", "BE", "AT"])
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_ec_ibgs"
           f"?format=JSON&lang=EN&{geos}&time=2024&unit=PC_IND&indic_is=I_BMED1&indic_is=I_BCBW"
           "&ind_type=IND_TOTAL&ind_type=F_Y25_54")
    _, body = polite.get(url)
    j = json.loads(body)
    dims, sizes = j["id"], j["size"]
    cats = {d: {v: k for k, v in j["dimension"][d]["category"]["index"].items()} for d in dims}
    rows = []
    for flat, val in j["value"].items():
        i, pos = int(flat), {}
        for d, s in zip(reversed(dims), reversed(sizes)):   # row-major: last dimension varies fastest
            pos[d] = cats[d][i % s]
            i //= s
        rows.append({**pos, "value": val, "status": (j.get("status") or {}).get(flat, "")})
    df = pd.DataFrame(rows)
    df["dataset"], df["extracted"], df["updated"] = "isoc_ec_ibgs", EXTRACTED, j.get("updated", "")
    save(df[["dataset", "geo", "time", "indic_is", "ind_type", "unit", "value", "status", "updated", "extracted"]],
         "eurostat_isoc_ec_ibgs")


# ------------------------------------------------------------------ 5. Wikipedia pageviews
def pageviews():
    arts = [("de.wikipedia", "Kollagen"), ("fr.wikipedia", "Collagène"), ("it.wikipedia", "Collagene"),
            ("nl.wikipedia", "Collageen"), ("es.wikipedia", "Colágeno")]
    out = []
    for proj, art in arts:
        for name in (art, quote(art)):
            url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{proj}/all-access/user/"
                   f"{name}/monthly/20231101/20261031")
            st, body = polite.get(url, robots=False)   # REST API, not a crawled page
            if st == 200:
                for it in json.loads(body)["items"]:
                    out.append({"project": proj, "article": art, "month": it["timestamp"][:6], "views": it["views"]})
                break
    save(pd.DataFrame(out), "wikipedia_collagen_pageviews")


# ------------------------------------------------------------------ 6. UCI Online Retail II
def uci():
    _, page = polite.get("https://archive.ics.uci.edu/dataset/502/online+retail+ii")
    lic = "CC BY 4.0" if re.search(r"Creative Commons Attribution 4\.0|CC BY 4\.0", page or "") else "not found"
    print(f"  UCI licence on the dataset page: {lic}")
    pq = PUB / "uci_invoices.parquet"
    if not pq.exists():
        _, z = polite.get("https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip", binary=True)
        xl = zipfile.ZipFile(io.BytesIO(z))
        name = [n for n in xl.namelist() if n.endswith(".xlsx")][0]
        sheets = pd.read_excel(io.BytesIO(xl.read(name)), sheet_name=None, engine="openpyxl")
        raw = pd.concat(sheets.values(), ignore_index=True)
        n0 = len(raw)
        raw = raw.drop_duplicates()                          # the two sheets overlap in December 2010
        n_dup = n0 - len(raw)
        raw["Invoice"] = raw["Invoice"].astype(str)
        is_return = raw["Invoice"].str.startswith("C")
        keep = raw[~is_return & raw["Customer ID"].notna() & (raw["Price"] > 0) & (raw["Quantity"] > 0)].copy()
        keep["amount_gbp"] = keep["Quantity"] * keep["Price"]
        inv = (keep.groupby(["Invoice", "Customer ID"], as_index=False)
                   .agg(invoice_ts=("InvoiceDate", "min"), amount_gbp=("amount_gbp", "sum"), lines=("StockCode", "size")))
        inv["customer_id"] = inv["Customer ID"].astype(int)
        inv = inv[["Invoice", "customer_id", "invoice_ts", "amount_gbp", "lines"]].rename(columns={"Invoice": "invoice"})
        inv.to_parquet(pq, index=False)
        save(pd.DataFrame([{"step": "rows in both sheets", "rows": n0}, {"step": "exact duplicate rows dropped", "rows": n_dup},
                           {"step": "returns (invoice starting with C)", "rows": int(is_return.sum())},
                           {"step": "missing Customer ID", "rows": int(raw["Customer ID"].isna().sum())},
                           {"step": "price or quantity <= 0", "rows": int(((raw["Price"] <= 0) | (raw["Quantity"] <= 0)).sum())},
                           {"step": "rows kept", "rows": len(keep)}, {"step": "invoices kept", "rows": len(inv)},
                           {"step": "licence", "rows": lic}]), "uci_cleaning_log")


# ------------------------------------------------------------------ 7. calendar and FX
def calendar():
    rows = []
    for y in (2024, 2025, 2026):
        for c in ["DE", "FR", "IT", "NL", "ES", "BE", "AT", "GB"]:
            st, body = polite.get(f"https://date.nager.at/api/v3/PublicHolidays/{y}/{c}", robots=False)
            if st == 200:
                rows += [{"country": c, "date": h["date"], "name": h["name"], "global": h.get("global")} for h in json.loads(body)]
    save(pd.DataFrame(rows), "public_holidays")
    st, body = polite.get("https://data-api.ecb.europa.eu/service/data/EXR/M.GBP.EUR.SP00.A?format=csvdata"
                          "&startPeriod=2024-11&endPeriod=2026-10", robots=False)
    fx = pd.read_csv(io.StringIO(body))[["TIME_PERIOD", "OBS_VALUE"]].rename(columns={"TIME_PERIOD": "month", "OBS_VALUE": "gbp_per_eur"})
    save(fx, "ecb_eur_gbp_monthly")


if __name__ == "__main__":
    PUB.mkdir(parents=True, exist_ok=True)
    import sys
    refresh = "--refresh" in sys.argv          # default: a step whose output exists is not re-collected
    outputs = {ashby: "job_board.csv", shop_home: "shop_stack.csv", catalogue: "glow25_catalogue.csv",
               articles: "glow25_articles_by_domain.csv", regulation: "eu_432_2012_collagen_claims.csv",
               eurostat: "eurostat_isoc_ec_ibgs.csv", pageviews: "wikipedia_collagen_pageviews.csv",
               uci: "uci_invoices.parquet", calendar: "ecb_eur_gbp_monthly.csv"}
    for step, out in outputs.items():
        if (PUB / out).exists() and not refresh:
            print(f"{step.__name__}: data/public/{out} exists, kept (use --refresh to collect again)")
            continue
        print(step.__name__)
        step()
    print(f"done ({date.today()})")
