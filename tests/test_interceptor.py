"""Unit tests for the deterministic red-flag interceptor."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akili_care import interceptor


class TriggerTests(unittest.TestCase):
    def test_english_chest_pain(self):
        alert = interceptor.screen("I have had chest pain since morning")
        self.assertIsNotNone(alert)
        self.assertEqual(alert.danger_sign, "chest_pain")

    def test_shona_chest_pain_case_insensitive(self):
        alert = interceptor.screen("Ndiri KURWADZIWA PACHIPFUVA zvakanyanya")
        self.assertIsNotNone(alert)
        self.assertEqual(alert.language, "sn")

    def test_ndebele_dyspnoea(self):
        alert = interceptor.screen("umama uthi ukuphefumula nzima")
        self.assertIsNotNone(alert)
        self.assertEqual(alert.danger_sign, "severe_dyspnoea")

    def test_snakebite_shona(self):
        alert = interceptor.screen("mwana akarumwa nenyoka kuminda")
        self.assertIsNotNone(alert)
        self.assertEqual(alert.danger_sign, "snakebite")

    def test_alert_card_has_holding_advice_and_lines(self):
        alert = interceptor.screen("she is bleeding heavily")
        self.assertIn("994 (ambulance)", alert.emergency_lines)
        self.assertTrue(alert.holding_advice)


class AdviserReviewTests(unittest.TestCase):
    """Signs added from the clinical adviser's review of 4 November 2026."""

    CASES = {
        "He has been coughing up blood since yesterday": "coughing_blood",
        "There is blood in his stool": "blood_in_stool_or_urine",
        "She has black stools since starting warfarin": "blood_in_stool_or_urine",
        "The child has sunken eyes and keeps vomiting": "severe_dehydration",
        "My father is very confused after the malaria": "confusion_or_drowsiness",
        "She says she is hallucinating on the new pills": "confusion_or_drowsiness",
        "He has a fever and a stiff neck": "stiff_neck",
        "Her face is drooping on the left": "stroke",
        "His speech is slurred": "stroke",
        "My baby is unable to breastfeed": "child_danger",
        "The baby is vomiting everything": "child_danger",
        "I am pregnant and bleeding": "obstetric",
        "The baby has stopped moving inside me": "obstetric",
        "My waters broke this morning": "obstetric",
        "I have very heavy period bleeding, soaking through pads": "heavy_menstrual_bleeding",
        "His breath smells fruity and he is vomiting": "blood_sugar_emergency",
        "She is shaking and sweating after her insulin": "blood_sugar_emergency",
        "Her lips are blue": "blue_lips",
        "I can't speak in full sentences": "severe_dyspnoea",
        "He cannot lie flat at night": "severe_dyspnoea",
        "My tongue is swelling after the amoxicillin": "severe_allergy",
        "His eyes are yellow since starting TB treatment": "jaundice",
        "There is ringing in my ears since the injection": "medicine_reaction",
        "He has a sickle cell crisis": "sickle_cell_crisis",
        "She has a severe headache": "severe_headache",
        "I have severe stomach pain on one side": "severe_abdominal_pain",
        "My grandmother collapsed in the kitchen": "unconscious",
        "Chest pressure going to my jaw": "chest_pain",
    }

    def test_each_case_triggers_expected_sign(self):
        for text, sign in self.CASES.items():
            with self.subTest(text=text):
                alert = interceptor.screen(text)
                self.assertIsNotNone(alert, text)
                self.assertEqual(alert.danger_sign, sign, text)

    def test_every_sign_has_holding_advice(self):
        for sign in interceptor.RED_FLAGS:
            with self.subTest(sign=sign):
                self.assertTrue(interceptor.HOLDING_ADVICE.get(sign))


class BenignTests(unittest.TestCase):
    def test_routine_headache_passes(self):
        self.assertIsNone(interceptor.screen("mwana ane musoro unorwadza"))

    def test_ambiguous_idiom_is_not_hard_triggered(self):
        # "moyo wangu unorwadza" is deliberately NOT a hard trigger: it is
        # ambiguous (grief / heartburn / cardiac) and is disambiguated by the
        # model's follow-up questions, then re-screened post-inference.
        self.assertIsNone(interceptor.screen("moyo wangu unorwadza"))

    def test_benefits_does_not_match_fits(self):
        self.assertIsNone(interceptor.screen("What are the benefits of the clinic?"))

    def test_everyday_confusion_passes(self):
        self.assertIsNone(interceptor.screen("I'm confused about my appointment time"))

    def test_mild_headache_passes(self):
        self.assertIsNone(interceptor.screen("I have a mild headache today"))


if __name__ == "__main__":
    unittest.main()
