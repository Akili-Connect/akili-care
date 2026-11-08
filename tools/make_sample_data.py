"""Generate the synthetic sample data in sample_data/.

Every number is random. Nothing here describes a real facility, patient or
programme. The files exist so the routing engine and the demo can run.

    python tools/make_sample_data.py
"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "sample_data"
rng = random.Random(2026)

DISTRICTS = [
    # district, province, settlement type, latitude, longitude
    ("Chipinge", "Manicaland", "Rural", -20.19, 32.62),
    ("Mutare", "Manicaland", "Urban", -18.97, 32.67),
    ("Lupane", "Matabeleland North", "Rural", -18.93, 27.81),
    ("Gwanda", "Matabeleland South", "Rural", -20.94, 29.00),
]
MONTHS = ["2026-05", "2026-06"]
FACILITY_TYPES = ["Clinic", "District hospital", "Mission hospital", "Mobile outreach point"]

H03 = ["month", "province", "district", "settlement_type", "latitude", "longitude",
       "facility_type", "outpatient_visits", "avg_wait_minutes",
       "essential_medicine_stockout_days", "telehealth_consultations",
       "network_uptime_pct", "referral_completion_pct", "patient_satisfaction_1_5",
       "service_pressure_level"]
H06 = ["month", "province", "district", "settlement_type", "latitude", "longitude",
       "language_code", "language_name", "channel", "content_type", "interactions",
       "query_success_rate_pct", "unresolved_query_rate_pct",
       "accessibility_issues_reported", "sentiment_score_minus1_to_1",
       "assistive_feature_usage_pct", "priority_improvement_area"]

LANGS = [("sn", "Shona"), ("nd", "Ndebele"), ("en", "English")]
CHANNELS = ["Community kiosk", "WhatsApp bot", "Voice line"]
CONTENT = ["Health information", "Clinic finder", "Appointment reminders"]
PRIORITIES = ["Voice support", "Simpler wording", "Response time", "Translation quality"]


def make_health():
    rows = []
    for month in MONTHS:
        for name, prov, kind, lat, lon in DISTRICTS:
            for ftype in FACILITY_TYPES:
                big = ftype == "District hospital"
                visits = rng.randint(900, 1600) if big else rng.randint(80, 450)
                wait = round(rng.uniform(40, 110), 1)
                stockout = rng.randint(1, 9) if ftype != "Mobile outreach point" else rng.randint(3, 20)
                uptime = round(rng.uniform(64, 94), 1)
                rows.append([month, prov, name, kind, lat, lon, ftype, visits, wait,
                             stockout, rng.randint(40, 340), uptime,
                             round(rng.uniform(55, 88), 1), round(rng.uniform(3.0, 4.5), 1),
                             rng.choice(["Low", "Medium", "High"])])
    return rows


def make_language():
    rows = []
    for month in MONTHS:
        for name, prov, kind, lat, lon in DISTRICTS:
            for code, lang in LANGS:
                rows.append([month, prov, name, kind, lat, lon, code, lang,
                             rng.choice(CHANNELS), rng.choice(CONTENT),
                             rng.randint(200, 1100), round(rng.uniform(58, 85), 1),
                             round(rng.uniform(12, 40), 1), rng.randint(5, 40),
                             round(rng.uniform(0.1, 0.7), 2), round(rng.uniform(10, 32), 1),
                             rng.choice(PRIORITIES)])
    return rows


def write(name, header, rows):
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


if __name__ == "__main__":
    write("03_health_access_sample.csv", H03, make_health())
    write("06_local_language_sample.csv", H06, make_language())
    print("wrote", OUT)
