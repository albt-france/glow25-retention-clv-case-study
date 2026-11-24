"""Polite HTTP helper for the public-data collector.

Rules applied to every request:
- robots.txt is read before the first request to a host; on top of it, paths that robots.txt disallows with
  wildcards (which urllib.robotparser does not understand) are blocked here explicitly;
- at most one request every 3 seconds to any Glow25 domain, one per second elsewhere;
- the first HTTP 429 (rate limit) stops all further requests to that host for the run: no retry;
- a neutral User-Agent with no personal contact details;
- every response body is cached in data/raw/ and never fetched twice.
"""
from __future__ import annotations

import hashlib
import time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "http"
USER_AGENT = "retention-case-study/1.0"
DELAYS = {"glow25": 3.0}   # every Glow25 country domain (glow25.de, .fr, .it, .nl, .es, .co.uk)
DEFAULT_DELAY = 1.0
# never fetched, whatever robots.txt says (cart, checkout, account, recommendations, sorting, rate-limited endpoint)
FORBIDDEN = ("/cart", "/checkout", "/account", "/orders", "/recommendations/products", "sort_by", "/products.json")
_last: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}
_blocked: set[str] = set()


def _host(url: str) -> str:
    return urlparse(url).netloc


def _allowed(url: str) -> bool:
    if any(f in url for f in FORBIDDEN):
        return False
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(root + "/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=20)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[root] = rp
        _last[p.netloc] = time.time()
    return _robots[root].can_fetch(USER_AGENT, url)


def _cache_path(url: str, headers: dict | None) -> Path:
    key = hashlib.sha256((url + repr(sorted((headers or {}).items()))).encode()).hexdigest()[:24]
    return CACHE / key


def get(url: str, headers: dict | None = None, binary: bool = False, robots: bool = True):
    """Return (status, body) from cache or network. body is bytes if binary else str; None on failure."""
    cp = _cache_path(url, headers)
    if cp.exists():
        raw = cp.read_bytes()
        status, body = int(raw[:3]), raw[4:]
        return status, (body if binary else body.decode("utf-8", "replace"))
    host = _host(url)
    if host in _blocked:
        print(f"[stopped] {host} returned 429 earlier: not fetched")
        return None, None
    if robots and not _allowed(url):
        print(f"[robots] disallowed, skipped: {url}")
        return None, None
    delay = next((d for h, d in DELAYS.items() if h in host), DEFAULT_DELAY)
    wait = delay - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.time()
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT, **(headers or {})}, timeout=120)
    except requests.RequestException as e:
        print(f"[error] {url}: {e}")
        return None, None
    if r.status_code == 429:
        _blocked.add(host)
        print(f"[429] {host}: rate limited, no further requests in this run")
        return 429, None
    CACHE.mkdir(parents=True, exist_ok=True)
    cp.write_bytes(f"{r.status_code:03d}\n".encode() + r.content)
    return r.status_code, (r.content if binary else r.text)
