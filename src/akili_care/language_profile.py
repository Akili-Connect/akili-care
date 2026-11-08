"""District language and accessibility profiles.

Binds a district language table (see ``sample_data/06_local_language_sample.csv``) to the UI adaptation
rules in ``data_binding_schema.json``: voice-first defaults, slowed TTS where
districts prioritise voice support, plain-register phrase packs, dialect tags.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

with open(ROOT / "data_binding_schema.json", encoding="utf-8") as fh:
    _UI = json.load(fh)["bindings"]["language_and_accessibility"]["ui_adaptations"]

DIALECT_MAP = {k: v for k, v in _UI["dialect_tag"].items() if k != "default"}


@dataclass
class DistrictProfile:
    district: str
    dialect_tag: str
    tts_rate: float
    default_modality: str
    plain_register: bool


def profile(district: str, csv_path: Path) -> DistrictProfile:
    """Build the UI profile for one district from the latest month of data."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            if rec["district"] == district:
                rows.append(rec)
    if not rows:
        raise ValueError(f"district not in dataset: {district}")
    latest = max(r["month"] for r in rows)
    rows = [r for r in rows if r["month"] == latest]

    priorities = {r["priority_improvement_area"] for r in rows}
    assistive = max(float(r["assistive_feature_usage_pct"]) for r in rows)
    majority_lang = Counter(r["language_code"] for r in rows).most_common(1)[0][0]

    return DistrictProfile(
        district=district,
        dialect_tag=DIALECT_MAP.get(district, majority_lang),
        tts_rate=0.85 if "Voice support" in priorities else 1.0,
        default_modality="voice-first" if assistive >= 20.0 else "text-first",
        plain_register="Simpler wording" in priorities,
    )
