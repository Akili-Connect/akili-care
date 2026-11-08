# Akili Care

An open-source health assistant for pregnant women, new mothers, caregivers and village health workers in Zimbabwe. It understands Shona, Ndebele and English, spots danger signs with fixed rules, and points people to a clinic that is likely to have medicine, staff and a working connection.

Built by [Akili Connect (Private) Limited](https://akiliconnect.com), Harare.

**Status: early prototype.** No patient or health worker has used it yet. It is not a medical device and must not be used to make real care decisions. See "Limits" below.

## The problem

Many maternal and newborn deaths follow danger signs that were noticed late. A woman or caregiver often has to decide alone whether a sign is serious and which clinic to go to, then travels far to a clinic with no medicine, no staff on duty or no connection. Most health tools are in English, while people describe symptoms in Shona or Ndebele, often in everyday words.

## How a message is handled

1. **Safety screen on the person's own words.** A fixed list of danger signs and phrases is checked first. If one matches, the conversation stops and the person is told to get emergency care now. The language model is never called.
2. **Language model.** If nothing matched, a model (Gemini through its public API) reads the message and replies in the same language. It also writes a one-line English summary and a danger flag. It is told never to diagnose or name medicines.
3. **Safety screen again, on the model's English summary.** This catches danger signs described in words our Shona and Ndebele lists do not contain yet. The model can add an escalation but can never clear one.
4. **Clinic routing.** If a clinic visit is advised, facilities are ranked on medicine stock, network uptime, waiting time, referral completion and distance. Facilities with stock at or below 40 percent, a degraded network or no staff are never recommended.

## What is in this repository

| Path | What it does |
|---|---|
| `src/akili_care/interceptor.py` | The danger-sign screen. 26 danger signs covering pregnancy, newborns, chronic conditions and medicine reactions. English is broad, Shona and Ndebele are a starter set. |
| `src/akili_care/assistant.py` | The full flow above. Needs a Gemini API key. |
| `src/akili_care/routing.py` | Stock-aware clinic ranking. |
| `src/akili_care/language_profile.py` | Per-district language and accessibility settings. |
| `src/akili_care/cli.py` | Command-line demo of the screen and routing. No key needed. |
| `src/akili_care/demo_conversations.py` | Runs 8 sample messages through the whole flow. Results are in `docs/demo_results.json`. |
| `sample_data/` | Synthetic data. Every number is random. Made by `tools/make_sample_data.py`. |
| `tests/` | 31 unit tests. The model is replaced by a stub, so no key or network is needed. |

## Try it

Python 3.10 or newer. Nothing to install.

```bash
# Run the tests
python3 -m unittest discover -s tests

# A danger sign: the screen stops the flow
PYTHONPATH=src python3 -m akili_care.cli --district Chipinge \
    --utterance "ndiri kurwadziwa pachipfuva"

# An ordinary question: routing runs
PYTHONPATH=src python3 -m akili_care.cli --district Chipinge \
    --utterance "mwana ane musoro unorwadza"

# The full flow with the language model
export GEMINI_API_KEY=your-key-here
PYTHONPATH=src python3 -m akili_care.demo_conversations
```

Never put a key in the code or commit a `.env` file.

## Sample data

The files in `sample_data/` are synthetic. They do not describe any real facility, patient or programme. A real deployment would feed the same fields from health ministry aggregate data and pharmacy stock returns, as described in `data_binding_schema.json`.

## Limits

- The Shona and Ndebele danger-sign lists are a starter set. They have not been checked by native-speaker panels or signed off by a registered nurse or doctor. The English list was reviewed by a medical student acting as clinical adviser, not by a licensed clinician.
- The 8 demo messages were written by the team, not by patients. Native speakers still need to check the Shona and Ndebele.
- Staffing is assumed true for every facility until a roster feed exists.
- Distances use a straight-line estimate multiplied by 1.3, not road distances.
- SMS, voice call and WhatsApp channels, offline use and an on-device model are planned, not built. See `docs/architecture.md`.
- The assistant never diagnoses or prescribes. It does not replace a nurse or a doctor. If you or someone near you is seriously unwell, go to the nearest clinic or hospital now.

## Contributing

We would especially like help with:

- Shona and Ndebele phrases for maternal and newborn danger signs, checked by native speakers, nurses or village health workers.
- Clinical review of the danger-sign list by registered clinicians.
- Test conversations in more languages and dialects, including Ndau.
- SMS and voice-call channels for basic phones.

Open an issue or pull request, or write to hello@akiliconnect.com. Please do not include real patient information in issues, examples or test data.

## Licence

Apache License 2.0. See `LICENSE`.
