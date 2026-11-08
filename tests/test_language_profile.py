"""Unit tests for district language and accessibility profiles."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akili_care.language_profile import profile

SAMPLE = Path(__file__).resolve().parents[1] / "sample_data" / "06_local_language_sample.csv"


class ProfileTests(unittest.TestCase):
    def test_chipinge_maps_to_ndau_register(self):
        self.assertEqual(profile("Chipinge", SAMPLE).dialect_tag, "sn-ndau")

    def test_lupane_maps_to_ndebele(self):
        self.assertEqual(profile("Lupane", SAMPLE).dialect_tag, "nd")

    def test_tts_rate_is_slowed_or_normal(self):
        self.assertIn(profile("Gwanda", SAMPLE).tts_rate, (0.85, 1.0))

    def test_unknown_district_raises(self):
        with self.assertRaises(ValueError):
            profile("Atlantis", SAMPLE)


if __name__ == "__main__":
    unittest.main()
