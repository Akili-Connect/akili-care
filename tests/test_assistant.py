"""Tests for the conversation flow, with the language model replaced by a stub.

No network and no API key are needed.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akili_care import assistant


def fake_model(**fields):
    base = {"language": "sn", "english_summary": "", "danger_sign_suspected": False,
            "needs_clinic": False, "reply": "Ndine urombo."}
    base.update(fields)
    return mock.patch.object(assistant, "_call_model", return_value=base)


class FlowTests(unittest.TestCase):
    def test_danger_phrase_stops_before_model(self):
        with mock.patch.object(assistant, "_call_model") as model:
            turn = assistant.respond("Ndine chipfuva chinorwadza", key="x")
        model.assert_not_called()
        self.assertEqual(turn.stage, "pre_screen")
        self.assertEqual(turn.alert.danger_sign, "chest_pain")

    def test_post_screen_catches_words_missing_from_lexicon(self):
        with fake_model(english_summary="The father is coughing up blood."):
            turn = assistant.respond("Baba vangu vari kukosora ropa", key="x")
        self.assertEqual(turn.stage, "post_screen")
        self.assertEqual(turn.alert.danger_sign, "coughing_blood")

    def test_model_flag_also_stops(self):
        with fake_model(english_summary="The person feels unwell.",
                        danger_sign_suspected=True):
            turn = assistant.respond("Handisi kunzwa zvakanaka", key="x")
        self.assertEqual(turn.stage, "model_flag")

    def test_routine_question_gets_reply_and_clinic(self):
        with fake_model(english_summary="The person has had a headache since yesterday.",
                        needs_clinic=True):
            turn = assistant.respond("Ndine musoro unorwadza", district="Chipinge", key="x")
        self.assertEqual(turn.stage, "answered")
        self.assertTrue(turn.clinic)

    def test_missing_key_raises(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                assistant.respond("Ndine musoro unorwadza")


if __name__ == "__main__":
    unittest.main()
