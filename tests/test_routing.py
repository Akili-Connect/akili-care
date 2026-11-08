"""Unit tests for the eligibility gate, derived fields and ranking score."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akili_care import routing
from akili_care.routing import Facility, WEIGHTS


def make(month="2026-06", district="Testville", ftype="Clinic", stockout=3,
         uptime=85.0, wait=60.0, referral=75.0, lat=-20.0, lon=32.0):
    fac = Facility(month=month, district=district, facility_type=ftype,
                   lat=lat, lon=lon, avg_wait_minutes=wait,
                   stockout_days=stockout, network_uptime_pct=uptime,
                   referral_completion_pct=referral)
    return routing.derive_fields(fac)


class DerivedFieldTests(unittest.TestCase):
    def test_stock_level_percentage_june(self):
        fac = make(month="2026-06", stockout=6)          # June has 30 days
        self.assertAlmostEqual(fac.stock_level_percentage, 80.0)

    def test_stock_level_percentage_march(self):
        fac = make(month="2026-03", stockout=15)         # March has 31 days
        self.assertAlmostEqual(fac.stock_level_percentage, (31 - 15) / 31 * 100)

    def test_network_status_threshold(self):
        self.assertEqual(make(uptime=70.0).network_status, "active")
        self.assertEqual(make(uptime=69.9).network_status, "degraded")


class GateTests(unittest.TestCase):
    def test_low_stock_excluded(self):
        fac = make(stockout=19)                          # 36.7% availability
        self.assertFalse(routing.passes_gate(fac))

    def test_degraded_network_excluded(self):
        fac = make(uptime=68.0)
        self.assertFalse(routing.passes_gate(fac))

    def test_healthy_facility_passes(self):
        self.assertTrue(routing.passes_gate(make()))

    def test_gate_never_routes_below_40(self):
        ranked, excluded = routing.route([make(stockout=19)], -20.0, 32.0)
        self.assertEqual(ranked, [])
        self.assertIn("stock", excluded[0].gate)


class RankingTests(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(WEIGHTS.values()), 1.0)

    def test_nearer_better_stocked_facility_ranks_first(self):
        near_good = make(district="Checheche", stockout=5, uptime=79,
                         wait=78, referral=71, lat=-20.61, lon=32.36)
        far_hospital = make(district="Chipinge", ftype="District hospital",
                            stockout=2, uptime=84, wait=96, referral=76,
                            lat=-20.19, lon=32.62)
        ranked, _ = routing.route([far_hospital, near_good], -20.60, 32.35)
        self.assertEqual(ranked[0].district, "Checheche")

    def test_score_within_unit_interval(self):
        ranked, _ = routing.route([make()], -20.0, 32.0)
        self.assertTrue(0.0 <= ranked[0].score <= 1.0)


if __name__ == "__main__":
    unittest.main()
