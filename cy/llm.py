"""Tiny Gemini client with a model fallback chain and a daily call cap.

The free tier has small per-model daily quotas, so we try the configured model first, then
lighter models with separate quotas. Callers always have a deterministic fallback."""
from __future__ import annotations

import os
import threading
import time
from datetime import date

import httpx

FALLBACKS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3-flash-preview"]
DAILY_CAP = int(os.environ.get("LLM_DAILY_CAP", "400"))
_state = {"day": None, "calls": 0, "dead": {}}
_lock = threading.Lock()


def _models() -> list[str]:
    first = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    return [first] + [m for m in FALLBACKS if m != first]


def generate(prompt: str, max_tokens: int = 200, temperature: float = 0.2, timeout: float = 25) -> tuple[str | None, str | None]:
    """Returns (text, model) or (None, None)."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None, None
    with _lock:
        today = date.today().isoformat()
        if _state["day"] != today:
            _state.update(day=today, calls=0, dead={})
        if _state["calls"] >= DAILY_CAP:
            return None, None
        _state["calls"] += 1
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    for model in _models():
        if _state["dead"].get(model, 0) > time.time():
            continue
        for attempt in range(2):
            try:
                r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                               headers={"x-goog-api-key": key}, json=body, timeout=timeout)
            except Exception:  # noqa: BLE001
                break
            if r.status_code == 429:  # quota gone for this model: skip it for an hour
                _state["dead"][model] = time.time() + 3600
                break
            if r.status_code in (500, 503):
                time.sleep(1.0 + attempt)
                continue
            if r.status_code != 200:
                break
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = " ".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            except (KeyError, IndexError):
                break
            if text:
                return text, model
            break
    return None, None
