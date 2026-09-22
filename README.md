# Find Pax v1.0.12 — Locked Scenario 2 Join / Transit

Release date: 2026-09-22

This release is built on the locked v1.0.6 production baseline and the Scenario 2 structure work. Existing Scenario 1, 3, 4 copy and Japan +81 validation remain protected.

## Scenario 2 structure

Selecting Scenario 2 now opens:

- **Join Pax** — message flow with Flight Number and Gate.
- **Transit Pax** — message flow with Flight Number and Gate, plus automatic destination mapping.
- **Call Directly** — same call-only behavior as the former **No message** option.

The former **No message** choice is not shown inside the Join / Transit detail page.

## Flight Number

Both Join Pax and Transit Pax show **Flight Number** above **final call at Gate**. `CX` is fixed and cannot be edited.

- **Join Pax:** accepts any 1–3 numeric CX flight digits. There is no flight whitelist.
- **Transit Pax:** accepts only CX450, CX451, CX530, CX531, CX564, CX565.

Transit destination mapping is locked as:

- CX450 → 東京成田 / Tokyo Narita / 東京（成田）
- CX564 → 大阪關西 / Osaka Kansai / 大阪（関西）
- CX530 → 名古屋中部 / Nagoya Chubu / 名古屋（中部）
- CX451 / CX565 / CX531 → 香港 / Hong Kong / 香港

## Scenario 2 language routing

Both Join Pax and Transit Pax support 中文 / English / 日本語.

- 中文 and English continue to use WhatsApp.
- 日本語 uses native SMS and the CTA displays `SMSを送信`.
- Scenario 2 Japanese SMS messages do **not** append the `cx.../SEC/date` suffix.
- Only **Transit Pax Japanese** appends the current Taipei time, calculated using `Asia/Taipei` and displayed as 24-hour `HH:mm`. Join Pax Japanese does not include Taipei time.

## Locked copy

`message-master.json` v1.3 is the human-readable copy master. `message-copy-lock.json` and `baseline-lock.json` store SHA-256 locks for the approved executable message generators and protected routing/validation functions.

The following are release-locked unless the user explicitly approves a change:

- Scenario 1 production copy, including the approved short Japanese SMS copy.
- Scenario 2 Join Pax Chinese / English / Japanese copy.
- Scenario 2 Transit Pax Chinese / English / Japanese copy.
- Transit flight-to-destination mapping and Taipei-time rule.
- Scenario 3 and Scenario 4 production copy.
- Japan +81 mobile validation and normalization behavior.
- Japanese SMS routing for Scenario 1 and Scenario 2 Join / Transit.

## Japan +81 phone baseline

The Japan-specific mobile validation remains unchanged: after country code 81 and tolerated leading zeroes, the number must normalize to a 10-digit mobile part starting 90, 80, 70, or 60. Japanese 020, 050, landlines and wrong lengths are rejected. Other countries retain existing validation.

## Release verification

Run:

```bash
python3 verify_release.py
```

A release is valid only when every check prints `PASS`. Do not alter lock hashes merely to silence an unexpected failure; only regenerate locks after explicitly approved protected changes.

## PWA / Offline

Service-worker cache identity is **v1.0.12** so deployed clients can refresh to the new release.

## v1.0.12 UI-only Scenario 2 update
- Passenger Type labels: Join Pax & Message / Transit Pax & Message / Call Directly.
- Passenger Type option text uses the existing brand teal; no icons are shown on this page.
- Message copy, routing, phone validation, flight rules, destination mapping, and SMS behavior remain locked and unchanged.

## v1.0.12 — Call Passenger 3 / 3 Destination display

The **Destination** row on the Call Passenger confirmation/preview page uses IATA airport codes:

- CX450 → NRT
- CX564 → KIX
- CX530 → NGO
- CX451 / CX565 / CX531 → HKG

This is a display-only change. Approved Transit passenger message copy continues to use the locked full destination names in Chinese / English / Japanese.

## v1.0.12 — Message Language + Scenario 3 Japanese

All four scenarios now use the heading **Message Language**.

Scenario 3 now includes a locked Japanese-only message option. Chinese/English behavior is unchanged. Scenario 3 Japanese is sent through WhatsApp, preserving the photo-sharing workflow.

## v1.0.12 — Scenario 3 Japanese removed

Scenario 3 is restored to Chinese / English only. The Japanese option and Japanese message introduced in v1.0.11 have been removed.

The approved UI change remains: all four scenarios use **Message Language** instead of **First Message Language**.
