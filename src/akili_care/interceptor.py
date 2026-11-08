"""Deterministic red-flag interceptor.

Screens every utterance BEFORE and AFTER model inference. This layer is pure
rules by design: clinical safety must never depend on a probabilistic model.
On a trigger, the conversational flow
terminates and a red alert card is returned.

Version 2 (5 November 2026): English triggers expanded from the clinical
adviser's review (voice notes of 4 November 2026: danger signs by condition
and medicine red flags). The original starter set was compiled from MoHCC /
WHO IMCI community danger-sign guidance.

Still open before any patient use:
- Shona and Ndebele phrases for the new signs (native-speaker panels).
- Sign-off by a registered nurse or doctor, including the holding advice.
  New signs use a general "go now" line until then.
- Every sign is treated as an emergency. Which signs should instead mean
  "nurse calls back today" has not been decided.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

EMERGENCY_LINES = ["994 (ambulance)", "MARS", "nearest staffed facility"]

#: danger sign -> language -> trigger phrases (lower-case).
#: English phrases must start at the beginning of a word ("fits" no longer
#: matches "benefits"). Shona and Ndebele phrases match anywhere in a word,
#: so stems such as "rumwa nenyoka" still catch "akarumwa nenyoka".
RED_FLAGS: dict[str, dict[str, list[str]]] = {
    "chest_pain": {
        "en": ["chest pain", "pain in my chest", "crushing chest",
               "chest pressure", "pressure in my chest", "chest tightness",
               "tight chest", "chest is tight",
               "pain going to my jaw", "pain spreading to my jaw",
               "pain going to my shoulder"],
        "sn": ["kurwadziwa pachipfuva", "chipfuva chinorwadza"],
        "nd": ["ubuhlungu esifubeni", "isifuba sibuhlungu"],
    },
    "severe_dyspnoea": {
        "en": ["cannot breathe", "can't breathe", "struggling to breathe",
               "short of breath", "difficulty breathing",
               "difficult breathing", "breathing fast", "fast breathing",
               "rapid breathing", "breathing very fast", "shallow breathing",
               "cannot speak in full sentences",
               "can't speak in full sentences", "cannot finish a sentence",
               "can't finish a sentence", "cannot lie flat", "can't lie flat",
               "frothy sputum", "chest indrawing", "chest is pulling in"],
        "sn": ["kutadza kufema", "kufema nematambudziko"],
        "nd": ["ukuphefumula nzima", "angikwazi ukuphefumula"],
    },
    "blue_lips": {
        "en": ["blue lips", "lips are blue", "lips turning blue",
               "lips have turned blue"],
        "sn": [],
        "nd": [],
    },
    "haemorrhage": {
        "en": ["bleeding heavily", "won't stop bleeding", "blood everywhere"],
        "sn": ["kubuda ropa rakawanda", "ropa harisi kumira"],
        "nd": ["ukopha kakhulu", "igazi kalimi"],
    },
    "coughing_blood": {
        "en": ["coughing blood", "coughing up blood", "cough up blood",
               "coughed up blood", "blood when i cough"],
        "sn": [],
        "nd": [],
    },
    "blood_in_stool_or_urine": {
        "en": ["blood in stool", "blood in my stool", "blood in the stool",
               "blood in his stool", "blood in her stool", "blood in their stool",
               "blood in his urine", "blood in her urine",
               "bloody stool", "bloody diarrhoea", "bloody diarrhea",
               "black stool", "black stools", "blood in urine",
               "blood in my urine", "blood in the urine"],
        "sn": [],
        "nd": [],
    },
    "severe_dehydration": {
        "en": ["rice water stool", "profuse diarrhoea", "profuse diarrhea",
               "profuse watery diarrhoea", "profuse watery diarrhea",
               "sunken eyes", "not passing urine", "no urine",
               "has not urinated", "hasn't urinated"],
        "sn": [],
        "nd": [],
    },
    "convulsions": {
        "en": ["convulsion", "seizure", "fitting", "fits"],
        "sn": ["kugwinha", "pfari"],
        "nd": ["ukuqhuqha", "izifo zokuwa"],
    },
    "unconscious": {
        "en": ["unconscious", "not waking up", "unresponsive", "collapsed",
               "fainted", "fainting", "passed out"],
        "sn": ["akafenda", "haasi kumuka"],
        "nd": ["uquleka", "akavuki"],
    },
    "confusion_or_drowsiness": {
        "en": ["very confused", "suddenly confused", "is confused and",
               "confused and", "not making sense", "hallucinat",
               "very sleepy", "unusually sleepy", "hard to wake",
               "difficult to wake", "can't stay awake", "cannot stay awake"],
        "sn": [],
        "nd": [],
    },
    "unable_to_sit_or_stand": {
        "en": ["cannot sit up", "can't sit up", "unable to sit",
               "cannot stand", "can't stand up", "unable to stand"],
        "sn": [],
        "nd": [],
    },
    "stiff_neck": {
        "en": ["stiff neck", "neck stiffness", "neck is stiff"],
        "sn": [],
        "nd": [],
    },
    "severe_headache": {
        "en": ["severe headache", "worst headache", "very bad headache"],
        "sn": [],
        "nd": [],
    },
    "stroke": {
        "en": ["face drooping", "face is drooping", "drooping face",
               "weakness on one side", "one side is weak", "one side weak",
               "can't move one side", "cannot move one side",
               "slurred speech", "speech is slurred", "slurring",
               "sudden loss of vision", "suddenly can't see",
               "suddenly cannot see", "lost my vision"],
        "sn": [],
        "nd": [],
    },
    "severe_abdominal_pain": {
        "en": ["severe abdominal pain", "severe stomach pain",
               "severe tummy pain", "severe pain in my stomach",
               "severe lower abdominal pain"],
        "sn": [],
        "nd": [],
    },
    "infant_fever": {
        "en": ["fever baby under two months", "newborn fever",
               "baby two weeks fever", "newborn has a fever",
               "newborn has fever", "newborn is hot", "newborn temperature"],
        "sn": ["mucheche ane fivha", "kacheche kane fivha"],
        "nd": ["usane olomkhuhlane", "umntwana omncane ulomkhuhlane"],
    },
    "child_danger": {
        "en": ["unable to breastfeed", "not breastfeeding",
               "can't breastfeed", "cannot breastfeed",
               "refusing to breastfeed", "unable to drink", "cannot drink",
               "can't drink anything", "vomiting everything",
               "vomits everything", "baby is very cold", "newborn is cold",
               "baby feels cold", "newborn yellow", "baby is yellow",
               "baby's eyes are yellow", "baby has yellow eyes",
               "baby's tummy is swollen", "baby's stomach is swollen",
               "swollen tummy"],
        "sn": [],
        "nd": [],
    },
    "obstetric": {
        "en": ["labour bleeding", "pregnant bleeding", "waters broke early",
               "pregnant and bleeding", "bleeding while pregnant",
               "bleeding in pregnancy", "baby not moving",
               "baby stopped moving", "baby has stopped moving",
               "baby moving less", "baby is moving less", "waters broke",
               "water broke", "waters have broken", "sudden gush",
               "headache in pregnancy", "pregnant with a severe headache"],
        "sn": ["kubuda ropa nepamuviri", "mimba kubuda ropa"],
        "nd": ["ukopha ukhulelwe", "isisu sokukhulelwa sibuhlungu kakhulu"],
    },
    "heavy_menstrual_bleeding": {
        "en": ["heavy menstrual bleeding", "very heavy period",
               "period won't stop", "soaking through pads",
               "soaking a pad every hour"],
        "sn": [],
        "nd": [],
    },
    "blood_sugar_emergency": {
        "en": ["sugar is very low", "low blood sugar", "sugar is low",
               "sugar dropped", "sugar is very high", "very high sugar",
               "fruity breath", "breath smells fruity",
               "shaking and sweating", "sweating and shaking"],
        "sn": [],
        "nd": [],
    },
    "sickle_cell_crisis": {
        "en": ["sickle cell crisis", "sickle cell pain"],
        "sn": [],
        "nd": [],
    },
    "severe_allergy": {
        "en": ["swollen tongue", "tongue is swelling", "tongue swelling",
               "throat is swelling", "throat swelling", "throat is closing",
               "swollen throat", "swollen lips", "lips are swelling",
               "lips swelling", "face is swelling", "swollen face",
               "allergic reaction"],
        "sn": [],
        "nd": [],
    },
    "jaundice": {
        "en": ["yellow eyes", "eyes are yellow", "eyes turning yellow",
               "eyes have turned yellow"],
        "sn": [],
        "nd": [],
    },
    "medicine_reaction": {
        "en": ["hearing loss", "lost my hearing", "suddenly can't hear",
               "ringing in my ears", "ringing in the ears", "ears are ringing",
               "tendon snapped", "tendon snap", "sudden tendon pain"],
        "sn": [],
        "nd": [],
    },
    "snakebite": {
        "en": ["snake bite", "bitten by a snake"],
        "sn": ["rumwa nenyoka"],  # stem match: kurumwa / akarumwa / varumwa
        "nd": ["ulunywe yinyoka"],
    },
    "self_harm": {
        "en": ["want to end my life", "kill myself", "suicide"],
        "sn": ["kuda kuzviuraya", "ndoda kuzviuraya"],
        "nd": ["ngifuna ukuzibulala"],
    },
}

#: Used for new signs until a clinician signs off specific first-aid lines.
GO_NOW = "Get to the nearest clinic or hospital now. Do not wait."

HOLDING_ADVICE = {
    "chest_pain": "Keep the person still and seated. Do not give food or drink.",
    "severe_dyspnoea": "Sit the person upright. Loosen tight clothing.",
    "haemorrhage": "Press firmly on the wound with a clean cloth. Do not remove it.",
    "convulsions": "Lay the person on their side. Do not put anything in the mouth.",
    "unconscious": "Lay the person on their side. Check breathing continuously.",
    "infant_fever": "Keep the baby lightly dressed. Go to a clinic immediately.",
    "obstetric": "Lie the mother on her left side. Travel to a facility now.",
    "snakebite": "Keep the limb still and below heart level. Do not cut or suck.",
    "self_harm": "Stay with the person. You are not alone; help is available.",
    "blue_lips": GO_NOW,
    "coughing_blood": GO_NOW,
    "blood_in_stool_or_urine": GO_NOW,
    "severe_dehydration": GO_NOW,
    "confusion_or_drowsiness": GO_NOW,
    "unable_to_sit_or_stand": GO_NOW,
    "stiff_neck": GO_NOW,
    "severe_headache": GO_NOW,
    "stroke": GO_NOW,
    "severe_abdominal_pain": GO_NOW,
    "child_danger": GO_NOW,
    "heavy_menstrual_bleeding": GO_NOW,
    "blood_sugar_emergency": GO_NOW,
    "sickle_cell_crisis": GO_NOW,
    "severe_allergy": GO_NOW,
    "jaundice": GO_NOW,
    "medicine_reaction": GO_NOW,
}


@dataclass
class AlertCard:
    """Payload rendered as the full-screen red alert (>= 4.5:1 contrast)."""

    danger_sign: str
    language: str
    matched_phrase: str
    emergency_lines: list[str] = field(default_factory=lambda: EMERGENCY_LINES)

    @property
    def holding_advice(self) -> str:
        return HOLDING_ADVICE[self.danger_sign]


def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return text.replace("’", "'")


def _matches(phrase: str, lang: str, probe: str) -> bool:
    needle = _normalise(phrase)
    if lang == "en":
        return re.search(r"(?<![a-z])" + re.escape(needle), probe) is not None
    return needle in probe


def screen(utterance: str) -> AlertCard | None:
    """Return an AlertCard if any red flag matches, else None.

    Runs in O(total phrase length); no model, no network, no state.
    """
    probe = _normalise(utterance)
    for sign, languages in RED_FLAGS.items():
        for lang, phrases in languages.items():
            for phrase in phrases:
                if _matches(phrase, lang, probe):
                    return AlertCard(danger_sign=sign, language=lang,
                                     matched_phrase=phrase)
    return None
