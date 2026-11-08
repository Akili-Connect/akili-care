"""Akili Care conversation turn: safety screen, language model, safety screen, routing.

Flow for every message:

1. Deterministic danger-sign screen on the patient's own words. If it fires,
   the model is never called.
2. Language model (Gemini, through the public REST API) reads the message in
   Shona, Ndebele or English. It returns a short reply in the same language,
   plus a plain-English summary of what the person said.
3. The same deterministic screen runs again on that English summary. This is
   the post-inference check: it catches danger signs described in words the
   Shona and Ndebele lexicon does not have yet. The model also flags any
   suspected danger sign; either one stops the flow.
4. If a clinic visit is advised, stock-aware routing adds the best clinic.

The model never decides that a case is safe. It can only add escalations.
It is told not to diagnose or prescribe.

Standard library only. The API key is read from the GEMINI_API_KEY
environment variable and is never stored in the repository.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import interceptor, routing
from .language_profile import profile

ROOT = Path(__file__).resolve().parents[2]
D03 = ROOT / "sample_data" / "03_health_access_sample.csv"
D06 = ROOT / "sample_data" / "06_local_language_sample.csv"
WARD_CENTROIDS = {          # same demo origins as cli.py
    "Chipinge": (-20.60, 32.35),
    "Mutare": (-18.97, 32.67),
    "Lupane": (-18.93, 27.81),
    "Gwanda": (-20.94, 29.00),
}

MODEL = os.environ.get("AKILI_MODEL", "gemini-flash-latest")
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM_PROMPT = """You are Akili Care, a health navigation assistant for patients, caregivers and village health workers in rural Zimbabwe.

Rules you must always follow:
- Reply in the same language the person used: Shona (including Ndau), Ndebele or English. Use simple, everyday words.
- Never diagnose. Never name or recommend a medicine or a dose. Never say a symptom is nothing to worry about.
- Keep replies to at most three short sentences. Ask at most one question.
- If anything could be serious, say clearly that they should go to a clinic, and that a nurse will follow up.
- Be warm and respectful.

Return JSON only, with these fields:
  "language": "sn", "nd" or "en"
  "english_summary": one plain-English sentence saying exactly what the person reported, including every symptom, in plain words
  "danger_sign_suspected": true or false (true for anything that might be an emergency, such as trouble breathing, coughing blood, confusion, convulsions, heavy bleeding, a baby not feeding, severe pain, or pregnancy problems)
  "needs_clinic": true or false
  "reply": your reply to the person, in their language
"""


@dataclass
class Turn:
    utterance: str
    stage: str                      # "pre_screen", "post_screen", "model_flag" or "answered"
    reply: str = ""
    language: str = ""
    english_summary: str = ""
    alert: interceptor.AlertCard | None = None
    clinic: str = ""
    raw: dict = field(default_factory=dict)


def _call_model(utterance: str, key: str, timeout: float = 60.0) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": utterance}]}],
        "generationConfig": {"temperature": 0.2,
                             "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        API.format(model=MODEL), data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    parts = data["candidates"][0]["content"]["parts"]
    text = next(p["text"] for p in parts if "text" in p and not p.get("thought"))
    return json.loads(text)


def _best_clinic(district: str) -> str:
    lat, lon = WARD_CENTROIDS[district]
    ranked, _ = routing.route(routing.load_facilities(D03), lat, lon)
    if not ranked:
        return "District hospital (no eligible clinic within the radius)"
    best = ranked[0]
    return (f"{best.name}, about {best.distance_km:.0f} km, "
            f"medicine stock {best.stock_level_percentage:.0f}%")


def respond(utterance: str, district: str = "Chipinge",
            key: str | None = None) -> Turn:
    # [1] deterministic screen on the person's own words
    alert = interceptor.screen(utterance)
    if alert:
        return Turn(utterance, "pre_screen", reply=alert.holding_advice,
                    language=alert.language, alert=alert)

    key = key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Set GEMINI_API_KEY to call the language model.")

    # [2] language model, constrained to short structured replies
    prof = profile(district, D06)
    prompt = utterance
    if prof.plain_register:
        prompt += "\n\n(Use very simple words.)"
    out = _call_model(prompt, key)

    turn = Turn(utterance, "answered", reply=out.get("reply", ""),
                language=out.get("language", ""),
                english_summary=out.get("english_summary", ""), raw=out)

    # [3] deterministic screen again, on the model's English summary
    post = interceptor.screen(turn.english_summary)
    if post:
        turn.stage, turn.alert = "post_screen", post
        return turn
    if out.get("danger_sign_suspected"):
        turn.stage = "model_flag"
        return turn

    # [4] stock-aware routing when a clinic visit is advised
    if out.get("needs_clinic"):
        turn.clinic = _best_clinic(district)
    return turn
