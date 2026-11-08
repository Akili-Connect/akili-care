"""Demo CLI: safety screen first, then stock-aware routing.

Examples
--------
Emergency (interceptor fires, no routing happens):
    python -m akili_care.cli --district Chipinge --utterance "kurwadziwa pachipfuva"

Routine triage question (routing runs):
    python -m akili_care.cli --district Chipinge --utterance "mwana ane musoro unorwadza"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from . import interceptor, routing
from .language_profile import profile

ROOT = Path(__file__).resolve().parents[2]
D03 = ROOT / "sample_data" / "03_health_access_sample.csv"
D06 = ROOT / "sample_data" / "06_local_language_sample.csv"

WARD_CENTROIDS = {          # demo patient origins (ward-level, spatially masked)
    "Chipinge": (-20.60, 32.35),
    "Mutare": (-18.97, 32.67),
    "Lupane": (-18.93, 27.81),
    "Gwanda": (-20.94, 29.00),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Akili Care routing demo")
    ap.add_argument("--district", default="Chipinge", choices=sorted(WARD_CENTROIDS))
    ap.add_argument("--utterance", required=True,
                    help="patient words, any of en / sn / nd")
    args = ap.parse_args()

    # [1] deterministic safety screen: ALWAYS before any model or routing
    alert = interceptor.screen(args.utterance)
    if alert:
        print("=" * 62)
        print("RED ALERT  |  danger sign:", alert.danger_sign,
              f"({alert.language}: '{alert.matched_phrase}')")
        print("CALL NOW   |", "  /  ".join(alert.emergency_lines))
        print("WHILE HELP COMES |", alert.holding_advice)
        print("=" * 62)
        print("Automated flow terminated. Session queued for nurse review.")
        return 1

    # [2] district language profile (dataset 06 binding)
    prof = profile(args.district, D06)
    print(f"[profile] {prof.district}: dialect={prof.dialect_tag} "
          f"tts_rate={prof.tts_rate} modality={prof.default_modality} "
          f"plain_register={prof.plain_register}")

    # [3] stock-aware routing (dataset 03 binding)
    lat, lon = WARD_CENTROIDS[args.district]
    facilities = routing.load_facilities(D03)
    ranked, excluded = routing.route(facilities, lat, lon)

    print(f"[routing] eligible facilities near {args.district} "
          f"(month {facilities[0].month}, sample pack covers 4 districts):")
    if not ranked:
        print("  no eligible facility within radius; fallback: district hospital")
    for i, fac in enumerate(ranked, 1):
        print(f"  {i}. {fac.name:38s} score={fac.score:.3f} "
              f"stock={fac.stock_level_percentage:.0f}% "
              f"uptime={fac.network_uptime_pct:.0f}% dist={fac.distance_km}km")
    for fac in excluded[:3]:
        print(f"  x  {fac.name:38s} {fac.gate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
