"""Optional language-model step for src/copy_lab.py. The repository runs without it (template fallback).

Used only when .env sets LLM_PROVIDER and LLM_API_KEY. The model receives aggregated themes only (no customer
data) and returns candidate subject lines; every line then goes through src/claims_check.py and a person.

Supported provider: LLM_PROVIDER=anthropic (official `anthropic` Python SDK, installed separately:
pip install anthropic). Optional: LLM_MODEL.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "claude-opus-5-5"
SYSTEM = (
    "You write email subject lines for a food-supplement brand. Return a JSON list of short subject lines (max 60 "
    "characters each). No health claims of any kind, no medical words, no promises of results, no dosage advice, "
    "no before/after. Use only the theme, product and action given."
)


def load_env() -> dict[str, str]:
    env = dict(os.environ)
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def available() -> bool:
    env = load_env()
    return bool(env.get("LLM_PROVIDER")) and bool(env.get("LLM_API_KEY"))


def subject_lines(brief: dict, n: int = 8) -> list[str] | None:
    """Candidate subject lines from the model, or None (no key, unsupported provider, refusal or API error)."""
    env = load_env()
    if not available() or env["LLM_PROVIDER"].lower() != "anthropic":
        return None
    try:
        import anthropic  # optional dependency
    except ImportError:
        return None
    client = anthropic.Anthropic(api_key=env["LLM_API_KEY"])
    try:
        response = client.messages.create(
            model=env.get("LLM_MODEL", DEFAULT_MODEL), max_tokens=2000, system=SYSTEM,
            messages=[{"role": "user", "content": f"Brief (JSON): {json.dumps(brief)}\nReturn {n} lines as a JSON list."}])
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        print(f"[language model] request failed, templates used instead: {e}")
        return None
    if response.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    try:
        lines = json.loads(text[text.index("["): text.rindex("]") + 1])
        return [str(x).strip() for x in lines if str(x).strip()][:n]
    except ValueError:
        return None
