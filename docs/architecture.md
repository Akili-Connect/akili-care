# Akili Care architecture

This page separates what exists today from what is planned.

## Built today

```
Message (Shona, Ndebele or English)
   |
   v
[1] Danger-sign screen (rules)  --match-->  stop, tell the person to get emergency care now
   |
   no match
   v
[2] Language model (Gemini API): reply in the person's language, English summary, danger flag
   |
   v
[3] Danger-sign screen again, on the English summary  --match-->  stop
   |        model danger flag                                    --->  stop
   v
[4] Clinic routing (stock, uptime, wait, referral completion, distance)
```

The screen and routing are deterministic and covered by unit tests. The model only interprets language. It can add an escalation but never remove one.

## Planned

- SMS and voice-call channels for basic phones, and WhatsApp for health workers.
- Reminders and check-ins for pregnant women and new mothers.
- Replacing the hosted model with open models served in Zimbabwe.
- Offline use on low-cost Android phones.
- Live stock and staffing feeds from facilities, replacing the sample data.
- Escalation delivery to a named nurse, with consent and data protection steps under Zimbabwe law.

None of the planned parts exist in this repository yet.
