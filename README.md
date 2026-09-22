# Find Pax v1.0.16 — Functional Fix Release

Release date: 2026-09-22

This release is built on the locked v1.0.6 production baseline and the Scenario 2 structure work. Existing Scenario 1, 3, 4 copy and Japan +81 validation remain protected.

## Scenario 2 structure

Selecting Scenario 2 now opens:

- **Join Pax & Message** — message flow with Flight Number, SEC and Gate.
- **Transit Pax & Message** — message flow with Flight Number, SEC and Gate, plus automatic origin/destination mapping.
- **Call Directly** — same call-only behavior as the former **No message** option.

The former **No message** choice is not shown inside the Join / Transit detail page.

## Flight Number

Both Join Pax and Transit Pax show **Flight Number** above **final call at Gate**. `CX` is fixed and cannot be edited.

- **Join Pax:** uses the approved general CX whitelist (same rule as Scenario 1 Join and Scenario 4 Disrupted flight).
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

`message-master.json` v1.7 is the human-readable copy master. `message-copy-lock.json` and `baseline-lock.json` store SHA-256 locks for the approved executable message generators and protected routing/validation functions.

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

Service-worker cache identity is **v1.0.16-r4**. The runtime asset list is explicitly declared and includes the locally bundled `libphonenumber-max.js`, so phone validation is available offline without a CDN dependency.

## v1.0.13 UI-only Scenario 2 update
- Passenger Type labels: Join Pax & Message / Transit Pax & Message / Call Directly.
- Passenger Type option text uses the existing brand teal; no icons are shown on this page.
- Message copy, routing, phone validation, flight rules, destination mapping, and SMS behavior remain locked and unchanged.

## v1.0.13 — Call Passenger 3 / 3 Destination display

The **Destination** row on the Call Passenger confirmation/preview page uses IATA airport codes:

- CX450 → NRT
- CX564 → KIX
- CX530 → NGO
- CX451 / CX565 / CX531 → HKG

This is a display-only change. Approved Transit passenger message copy continues to use the locked full destination names in Chinese / English / Japanese.

## v1.0.13 — Message Language + Scenario 3 Japanese

All four scenarios now use the heading **Message Language**.

Scenario 3 now includes a locked Japanese-only message option. Chinese/English behavior is unchanged. Scenario 3 Japanese is sent through WhatsApp, preserving the photo-sharing workflow.

## v1.0.13 — Scenario 3 Japanese removed

Scenario 3 is restored to Chinese / English only. The Japanese option and Japanese message introduced in v1.0.11 have been removed.

The approved UI change remains: all four scenarios use **Language**.

## v1.0.13 — Scenario 1 Passenger Type

Scenario 1 now opens the same clean Passenger Type layer as Scenario 2:
- Join Pax & Message — existing locked Chinese / English / Japanese copy.
- Transit Pax & Message — newly locked Chinese / English / Japanese copy.
- Call Directly — same call-only WhatsApp logic as Scenario 2.

Existing v1.0.12 behavior is preserved, including Message Language headings, Scenario 3 Chinese/English only, +81 validation, and Scenario 2 IATA Destination codes (NRT / KIX / NGO / HKG).

Japanese native SMS keeps the existing platform split: iOS uses `&body=` and Android uses `?body=`.

## v1.0.14
- All Message Language headings renamed to Language.
- Scenario 1 Join Japanese SMS replaced with newly approved copy.
- Scenario 1/2 Transit SEC shows Origin IATA: CX450/530/564 HKG; CX451 NRT; CX531 NGO; CX565 KIX.
- General CX whitelist applied to Scenario 1 Join, Scenario 2 Join and Scenario 4 Disrupted flight.
- Transit, Scenario 3 Arrival, Connecting Flight and Protect to remain exceptions; Protect to allows non-CX.

## v1.0.15 — Lightweight Images
- PNG assets recompressed/reduced-color for faster loading on company phones.
- Image dimensions, filenames, UI layout, message copy, flight rules, validation, SMS and WhatsApp behavior are unchanged.

## v1.0.16 — Functional fixes
- Fixed Service Worker installation by declaring the exact runtime `ASSETS` list and bumping cache identity to v1.0.16. `libphonenumber-js` 1.12.29 `bundle/libphonenumber-max.js` is bundled locally and precached, removing the runtime CDN dependency.
- Phone validation now requires `PhoneNumber.isValid()` when available and returns canonical E.164 digits, fixing country-code + domestic-trunk-zero inputs such as `886 0912...`, `86 0138...`, and `82 010...`.
- Japan +81 validation is restricted to 90 / 80 / 70 / 60 mobile prefixes only.
- Scenario 2 Transit release verification follows the current `callSecPrefix` SEC-origin UI.
- Scenario 3 and 4 reset message-language ordering on entry; Scenario 4 defaults to English First.
- `dateCode()` now uses `Asia/Taipei`, matching `taipeiTime()`.
- Scenario 4 Connecting flight / Protect to airline codes accept two alphanumeric IATA designators such as 5J, 3K and 7C.
- Approved message copy is unchanged.

- v1.0.16 UI hotfix: restored visible `罐頭號碼 無用` phone warning; phone validation and approved message copy unchanged.
## v1.0.16 — UI / State navigation hotfix

- Back / Next within the same flow continues to preserve entered values for easy correction.
- Re-entering Scenario 1, 2, 3, or 4 from the Scenario screen now starts that scenario with clean case fields, preventing values from a previous case from enabling Next.
- Changing Scenario 1 or Scenario 2 Passenger Type clears fields that belong to the previous type. Scenario 2 now also clears the old Gate value.
- Scenario 1 and Scenario 2 progress labels include the selected passenger type (Join Pax / Transit Pax). Scenario 2 Join / Transit remains fixed at five steps. Call Directly hides the progress bar and shows the phone number inside Confirm details instead of the top-right passenger badge.
- Opening Message Preview without editing no longer creates a saved custom draft when navigating Back; generated Japanese Transit time can therefore refresh normally. Actual typed edits remain preserved per language.
- Both blocked canned/test phone numbers now show `罐頭號碼 無用`, including entries that libphonenumber itself considers invalid.
- Approved message copy, Japan +81 rules, SEC/IATA rules, SMS/WhatsApp routing, and visual styling are unchanged.
