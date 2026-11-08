"""Stock-aware clinic routing engine.

Implements the eligibility gate and ranking score defined in
``data_binding_schema.json`` (single source of truth, shipped at repo root)
against a facility table shaped like ``sample_data/03_health_access_sample.csv``.

Derived fields:

    stock_level_percentage = (days_in_month - stockout_days) / days_in_month * 100
    network_status         = "active" if network_uptime_pct >= 70 else "degraded"

Gate:   stock_level_percentage > 40  AND  network_status == "active"
Score:  R = 0.30*S + 0.20*U + 0.15*(1 - W) + 0.15*C + 0.20*(1 - D)
        with all terms scaled to the unit interval.
"""

from __future__ import annotations

import calendar
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "data_binding_schema.json"

ROAD_FACTOR = 1.3          # straight-line to road-distance approximation
WAIT_CAP_MIN = 150.0       # normalisation cap for waiting time
DIST_CAP_KM = 50.0         # normalisation cap for road distance


def _load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as fh:
        return json.load(fh)


SCHEMA = _load_schema()
WEIGHTS = SCHEMA["bindings"]["clinic_routing"]["ranking_weights"]


@dataclass
class Facility:
    """One facility-month row from dataset 03, with derived routing fields."""

    month: str
    district: str
    facility_type: str
    lat: float
    lon: float
    avg_wait_minutes: float
    stockout_days: int
    network_uptime_pct: float
    referral_completion_pct: float
    stock_level_percentage: float = 0.0
    network_status: str = "degraded"
    staffed: bool = True               # roster feed lands at pilot; default true
    distance_km: float = 0.0
    score: float = 0.0
    gate: str = ""

    @property
    def name(self) -> str:
        return f"{self.district} {self.facility_type}"


def days_in_month(month: str) -> int:
    """Days in a YYYY-MM month string."""
    year, mon = (int(x) for x in month.split("-"))
    return calendar.monthrange(year, mon)[1]


def derive_fields(fac: Facility) -> Facility:
    """Compute the two derived routing fields documented in the schema."""
    dim = days_in_month(fac.month)
    fac.stock_level_percentage = (dim - fac.stockout_days) / dim * 100.0
    fac.network_status = "active" if fac.network_uptime_pct >= 70.0 else "degraded"
    return fac


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    rad = math.radians
    dlat, dlon = rad(lat2 - lat1), rad(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def passes_gate(fac: Facility) -> bool:
    """Hard eligibility gate: never route to stock <= 40% or degraded network."""
    return (fac.stock_level_percentage > 40.0
            and fac.network_status == "active"
            and fac.staffed)


def rank_score(fac: Facility) -> float:
    """Weighted ranking score over unit-scaled terms."""
    s = fac.stock_level_percentage / 100.0
    u = fac.network_uptime_pct / 100.0
    w = min(fac.avg_wait_minutes / WAIT_CAP_MIN, 1.0)
    c = fac.referral_completion_pct / 100.0
    d = min(fac.distance_km / DIST_CAP_KM, 1.0)
    return (WEIGHTS["stock"] * s
            + WEIGHTS["uptime"] * u
            + WEIGHTS["inverse_wait"] * (1.0 - w)
            + WEIGHTS["referral_completion"] * c
            + WEIGHTS["inverse_distance"] * (1.0 - d))


def load_facilities(csv_path: Path, month: str | None = None) -> list[Facility]:
    """Load facility-month rows; keep only the requested (or latest) month."""
    rows: list[Facility] = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            rows.append(Facility(
                month=rec["month"],
                district=rec["district"],
                facility_type=rec["facility_type"],
                lat=float(rec["latitude"]),
                lon=float(rec["longitude"]),
                avg_wait_minutes=float(rec["avg_wait_minutes"]),
                stockout_days=int(rec["essential_medicine_stockout_days"]),
                network_uptime_pct=float(rec["network_uptime_pct"]),
                referral_completion_pct=float(rec["referral_completion_pct"]),
            ))
    target = month or max(r.month for r in rows)
    return [derive_fields(r) for r in rows if r.month == target]


def route(facilities: list[Facility], patient_lat: float, patient_lon: float,
          top_n: int = 3, max_radius_km: float = 150.0,
          ) -> tuple[list[Facility], list[Facility]]:
    """Return (ranked eligible facilities, gate-excluded facilities).

    Facilities beyond ``max_radius_km`` road distance are excluded up front:
    the assistant never recommends a journey longer than a district referral
    pathway. If nothing is eligible within the radius, callers fall back to
    the district hospital plus an explanatory message (see cli.py).
    """
    eligible, excluded = [], []
    for fac in facilities:
        fac.distance_km = round(
            haversine_km(patient_lat, patient_lon, fac.lat, fac.lon) * ROAD_FACTOR, 1)
        if fac.distance_km > max_radius_km:
            fac.gate = f"fail: beyond {max_radius_km:.0f} km radius"
            excluded.append(fac)
            continue
        if passes_gate(fac):
            fac.gate = "pass"
            fac.score = round(rank_score(fac), 3)
            eligible.append(fac)
        else:
            fac.gate = ("fail: stock <= 40%"
                        if fac.stock_level_percentage <= 40.0
                        else "fail: network degraded" if fac.network_status != "active"
                        else "fail: unstaffed")
            excluded.append(fac)
    eligible.sort(key=lambda f: f.score, reverse=True)
    return eligible[:top_n], excluded
