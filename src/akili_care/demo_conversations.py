"""Run sample conversations through the full Akili Care flow and save the results.

    GEMINI_API_KEY=... python -m akili_care.demo_conversations

Writes docs/demo_results.json and prints a readable transcript. The sample
sentences were written by the team, not by patients; native speakers still
need to check the Shona and Ndebele.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from .assistant import MODEL, respond

ROOT = Path(__file__).resolve().parents[2]

SAMPLES = [
    ("Chipinge", "Ndine musoro unorwadza kubvira nezuro"),
    ("Chipinge", "Mwana wangu ane fivha uye haasi kuyamwa"),
    ("Mutare", "Baba vangu vari kukosora ropa"),
    ("Lupane", "Ngilomkhuhlane lekhanda elibuhlungu"),
    ("Gwanda", "Umntwana wami uhlanza konke akudlayo"),
    ("Mutare", "My mother takes metformin and today she is very weak and breathing fast"),
    ("Chipinge", "Ndine chipfuva chinorwadza"),
    ("Mutare", "When is the clinic open on Saturday?"),
]

LABELS = {
    "pre_screen": "STOPPED by the safety screen before the model",
    "post_screen": "STOPPED by the safety screen on the model's English summary",
    "model_flag": "STOPPED: the model flagged a possible danger sign",
    "answered": "Answered",
}


def main() -> int:
    results = []
    for district, text in SAMPLES:
        turn = respond(text, district)
        rec = {
            "district": district, "message": text, "outcome": LABELS[turn.stage],
            "language": turn.language, "english_summary": turn.english_summary,
            "danger_sign": turn.alert.danger_sign if turn.alert else "",
            "reply": turn.reply, "clinic": turn.clinic,
        }
        results.append(rec)
        print(f"\n[{district}] {text}")
        print(f"  -> {rec['outcome']}"
              + (f" ({rec['danger_sign']})" if rec["danger_sign"] else ""))
        if turn.english_summary:
            print(f"  summary: {turn.english_summary}")
        print(f"  reply:   {turn.reply}")
        if turn.clinic:
            print(f"  clinic:  {turn.clinic}")
        time.sleep(1)
    out = {"model": MODEL, "run_at": time.strftime("%Y-%m-%d %H:%M"),
           "results": results}
    path = ROOT / "docs" / "demo_results.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
