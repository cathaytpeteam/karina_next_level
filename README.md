# r34 Stable Baseline

**r34 is the user-approved stable baseline.** Existing locked behavior, layout, navigation, validation, message copy, and PWA behavior must not be changed unless the user explicitly authorizes that exact change.

Before any future release, read `STABLE-BASELINE-CHECKLIST.md` and run the existing regression verifiers. Do not update lock hashes merely to silence an unexpected failure.

---

# Find Pax v1.1 — Golden Layout Baseline

Release date: 2026-09-22

This release is built on the locked v1.0.6 production baseline and the Scenario 2 structure work. Existing Scenario 1, 3, 4 copy and Japan +81 validation remain protected.

## Golden Layout Lock (v1.1)

The currently approved page structure and field placement are now release-locked. `layout-lock.json` records the approved screen order, exact protected screen markup hashes, field/control order, progress/header DOM, Confirm details placement, and bottom CTA/footer DOM. `verify_layout.py` fails if those protected areas change.

**Policy:** do not regenerate `layout-lock.json` hashes merely to make a failed build pass. A layout hash may be updated only after the user explicitly approves the specific UI/layout change. Business logic and approved message copy remain protected separately by the existing baseline/message locks.

Run `python3 verify_layout.py` for the layout-only guard, or `python3 verify_release.py` for the full release guard (which now includes the layout check).

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

Service-worker cache identity is **v1.1-r4**. The runtime asset list is explicitly declared and includes the locally bundled `libphonenumber-max.js`, so phone validation is available offline without a CDN dependency.

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
- Scenario 2 Final Call no longer has an SEC page; SEC-origin UI applies only to Scenario 1.
- Scenario 3 and 4 reset message-language ordering on entry; Scenario 4 defaults to English first.
- `dateCode()` now uses `Asia/Taipei`, matching `taipeiTime()`.
- Scenario 4 Connecting flight / Protect to airline codes accept two alphanumeric IATA designators such as 5J, 3K and 7C.
- Approved message copy is unchanged.

- v1.0.16 UI hotfix: restored visible `罐頭號碼 無用` phone warning; phone validation and approved message copy unchanged.
## v1.0.16 — UI / State navigation hotfix

- Back / Next within the same flow continues to preserve entered values for easy correction.
- Re-entering Scenario 1, 2, 3, or 4 from the Scenario screen now starts that scenario with clean case fields, preventing values from a previous case from enabling Next.
- Changing Scenario 1 or Scenario 2 Passenger Type clears fields that belong to the previous type. Scenario 2 now also clears the old Gate value.
- Scenario 1 and Scenario 2 progress labels place numeric progress before the selected passenger type: `Flow - N/N - Join Pax / Transit Pax`. Scenario 2 Join / Transit remains fixed at four steps. Call Directly is a separate one-page branch and shows `1/1 - Call Directly`; the phone number remains inside Confirm details instead of the top-right passenger badge.
- Opening Message Preview without editing no longer creates a saved custom draft when navigating Back; generated Japanese Transit time can therefore refresh normally. Actual typed edits remain preserved per language.
- Both blocked canned/test phone numbers now show `罐頭號碼 無用`, including entries that libphonenumber itself considers invalid.
- Approved message copy, Japan +81 rules, SEC/IATA rules, SMS/WhatsApp routing, and visual styling are unchanged.


## Authorized SEC layout update (r5)
Scenario 1 and Scenario 2 SEC screens are now visually unified as one inline field: `[ IATA | SEC ]`. Join uses `TPE`; Transit derives `HKG`, `NRT`, `NGO`, or `KIX` from the selected transit flight. This was an explicitly authorized exception to the Golden Layout Lock; the updated SEC layout is locked again in `layout-lock.json`.

## Authorized progress update (r6)

All progress labels are locked at **20px / 700**. Scenario 1 uses `漏查 - N/3 - Join Pax / Transit Pax`; Scenario 2 uses `Final Call - N/4 - Join Pax / Transit Pax`. Before Passenger Type is selected, only `Flow - N/N` is shown.

## Authorized responsive keyboard / Safe Area adjustment
- iOS/Android keyboard mode keeps the approved 20px/700 progress label visible.
- The header continues to respect `safe-area-inset-top`.
- Input-form screens vertically use the visible workspace above the CTA instead of leaving the form pinned to the top with a large unused gap.
- Screen order, field order, SEC layout, copy, validation rules and CTA styling remain locked.

## Authorized read-only Message Preview update (r8)
All Message Preview screens are now read-only. The in-app `Edit` and `Copy Text` controls have been removed by explicit user approval. Message text can still be reviewed with `View`, then adjusted/copied in WhatsApp or the native SMS app after handoff. This behavior is now part of the locked release baseline.


## Authorized final visual / suffix tuning (r9)
- `中文在前`, `English first`, and `日本語のみ` preview-order labels use **18px / 700**.
- Scenario 3 `無人領取的行李` uses **18px / 700** and sits to the **left** of the Bag Tag 1 input group on the same row.
- Progress names remain **20px / 700**; the numeric progress (`1/3`, `3/5`, etc.) uses a lighter gray-green to separate it visually from the flow name.
- Scenario 1 Join suffix is shortened from `cx450/000/23Sep` style to `450/000`. Japanese and paths without a suffix remain unchanged.
- These changes were explicitly authorized and are locked again in the release baseline.

- Passenger Type hierarchy: Join is the large primary action; Transit and Call Directly are smaller secondary actions.
- Progress counters are compact (`1/4`, `2/4`, etc. for Final Call).

## v1.1 — PWA icon deduplication
- Removed duplicate `icon-maskable-192.png` and `icon-maskable-512.png` files.
- `icon-192.png` and `icon-512.png` now serve both `any` and `maskable` manifest purposes.
- Service Worker cache revision bumped to **v1.1-r2**. App UI, message copy, validation and workflow behavior are unchanged.


## v1.1 Final Call naming lock
Scenario 2 is named **Final Call**. Its current message-path progress is locked to **Final Call - 1/4 - Join Pax/Transit Pax → Final Call - 4/4 - Join Pax/Transit Pax**, with the SEC page removed for Join and Transit. Scenario 1 now counts **Passenger Type as 1/3**, then Flight as **2/3** and SEC as **3/3**; the read-only preview keeps the completed **3/3** state visible. After a Join/Transit choice, Passenger Type becomes a trailing annotation, e.g. **漏查 - 2/3 - Join Pax**. `navigation-lock.json` + `verify_navigation.py` protect this mapping, step order, and entry/type routing from regression.


## Authorized Scenario 2 SEC removal (r6)
Scenario 2 **Final Call** no longer asks for SEC for either Join Pax or Transit Pax. The locked message path is **Passenger Type → Flight Number → Gate → Message Preview**, with progress **1/4 → 4/4** and Passenger Type shown as the trailing annotation after selection. Scenario 1 SEC and its 1/3 → 3/3 flow are unchanged.

- Back-state lock: returning from Scenario 1/2 message flow to Passenger Type hides the prior Join/Transit annotation; the type page shows only `漏查 - 1/3` or `Final Call - 1/4`.

- Call Directly progress lock: Scenario 1 displays `漏查 - 1/1 - Call Directly`; Scenario 2 displays `Final Call - 1/1 - Call Directly`. Join/Transit step counts are unchanged.


## v1.1 consistency fixes (r9)
- Manifest now provides separate `any` and padded `maskable` icons.
- Browser history state distinguishes Back and Forward; Safari Forward restores the forward screen instead of popping backward.
- Disrupted Pax Confirm details no longer breaks the word “Arrangement” at arbitrary characters.
- Final Call Flight Number field CSS selectors now match the aligned 72px CX layout used elsewhere.
- Scenario 1 Confirm details SEC now includes its IATA prefix (for example `TPE 008`).
- Removed the “Please select a listed CX flight” helper text while keeping whitelist validation unchanged.


## v1.1 Scenario 4 Flight Type flow lock
- Disrupted Pax starts at **Flight Type** (1/6), visually aligned with Passenger Type, including title/header placement.
- Options: **Tight Connection** (large primary), **Delayed**, **To be updated**. Each choice navigates directly to 2/6; Flight Type has no footer/Next.
- **Delayed to** is merged into **Disrupted flight** (2/6) and is visible/required only when Delayed is selected.
- Tight Connection and To be updated do not depend on delayed-time validation.
- Existing remaining steps keep their order through 6/6.
- `verify_navigation.py` now guards direct choice navigation, no-Next behavior, Delayed-only validation ownership, Flight Type title/header placement, Back/Forward state handling, and the full 1/6→6/6 mapping.
- Release build was also exercised in a 390×844 headless Chromium smoke test for all three Flight Type branches, Back/Forward, and To be updated through 6/6.
- Message copy, phone validation, Scenario 1, Scenario 2, and Scenario 3 behavior remain protected.
- Service worker cache revision: **v1.1-r11**.


## r12 Scenario 4 input regression
- Delayed: entering a valid three-digit TPE-departure CX flight (for example 407) automatically focuses Delayed to.
- Delayed to accepts HHMM and formats it as HH:MM.
- Disrupted flight uses the locked TPE-departure CX whitelist; a non-whitelist flight is visibly invalid and cannot continue.
- Regression guards added to verify_navigation.py.

## r15 — Disrupted flight 2/6 · Delayed to
- Bug fix: the Delayed to time field had only one child inside the shared `[prefix | value]` grid, so it was squeezed into the 72px prefix column; `18:00` overflowed and scrolled its first digit out of view (displayed as `8:00`). The stored value and message were already `18:00`; this was display-only.
- Layout (CSS only, protected `s-dflight` markup unchanged): clock prefix chip aligns `18:00` with `CX 407`; centered divider label `DELAYED TO`; `HH:MM` placeholder; red border for invalid times (e.g. 25:75).
- SW cache r15.

## r16 — Disrupted Pax 4/6 · Flight arrangement
- Visual alignment with the rest of the app (CSS only; protected `s-darrange` markup and control order unchanged): option labels now use brand teal, left-aligned 20px/800 like the other choice cards, with a radio indicator on the right.
- When "Will protect to" is selected, its CX flight / DEP time fields appear directly beneath that option (visual order via CSS), with "Arrange in airport" below.
- Validation, message copy and navigation unchanged. SW cache r16.

## r17 — Flight Type label locked as "Suspended"
- User-approved: Scenario 4 Flight Type third option is "Suspended" (formerly "To be updated"). It still maps to status `unknown`; routing, copy and validation unchanged.
- `layout-lock.json` (s-dstatus hash), `navigation-lock.json`, `verify_navigation.py` and `verify_release.py` updated to the approved label. `verify_release.py` now passes all checks.

## r18 — Step title stays on one line (Android)
- On narrower Android screens (e.g. 360px wide with Roboto), "Disrupted Pax - 2/6 - Tight connection" wrapped to two lines. The step title is now single-line and auto-shrinks from 20px (min 13px) to fit the width; ellipsis only as a last resort. Applies to every flow's step title; wording unchanged.
- SW cache r18.

## r19 — Disrupted Pax 3/6 Connecting flight: block TPE departures
- The Connecting flight is the onward flight after arriving in HKG, so any whitelisted CX flight departing TPE (the same 21-flight list used for the Disrupted flight on 2/6) is rejected when the airline code is CX: red field border, red hint "Departs TPE — not allowed", Next disabled.
- Other CX numbers and non-CX airline codes are unaffected. SW cache r19.

## r20 — "Flight from TPE" + red borders across Scenario 1–4
- Scenario 4 step 2/6 (all Flight Types): title is the single line "Flight from TPE"; the TPE chip is removed (user-authorized; `layout-lock.json` s-dflight re-locked). Preview row label "Disrupted flight" unchanged.
- New `markInvalidFields()` runs on every render and gives a red border to any filled input that breaks its rule:
  - S1 漏查: flight (Join = TPE whitelist, Transit = CX450/451/530/531/564/565), SEC > 580.
  - S2 Final Call: flight (same Join / Transit rules, unchanged).
  - S3 Wrong Pick-up: flight not 1–3 digits.
  - S4 Disrupted Pax: flight from TPE not whitelisted; connecting flight with invalid airline code or a CX TPE-departure flight; Will-protect-to invalid airline code / number; any time outside 00:00–23:59.
- Empty fields and half-typed times stay neutral. Validation rules themselves unchanged. SW cache r20.

## r21 — Flow behaviour regression (`verify_behavior.py`)
The older verifiers prove files are intact and locked HTML/copy is unchanged. `verify_behavior.py` drives the real app in headless Chromium and is now part of `verify_release.py`.

Setup once: `pip install playwright && python -m playwright install chromium`. Run: `python3 verify_release.py` (≈40 s) or `python3 verify_behavior.py` alone.

What it enforces, from `flow-behavior-spec.json`:
1. **Static route scan** — every `go(...)` route reachable from a button handler or the NEXT map must equal the spec's routes, and every "n/N" in the spec must match `FLOWS[].steps`. Moving a page or re-routing a button fails and names the moved screen.
2. **Control inventory** — every screen and every button on a screen must be in the spec; a new button with no branch fails.
3. **All 62 outgoing branches executed** on every run (screen, progress title, progress bar, Next enabled). Any transition not in the spec fails as "unexpected".
4. **Back + browser Forward** checked after each of the 40 in-app branches.
5. **20 guards** — invalid input keeps Next disabled and shows a red border (S1–S4 rules, canned phone numbers).
6. **8 state rules** — mode switch clears inputs, same mode keeps them, Flight Type switch clears Delayed time, Enter advances, Back keeps inputs, re-entering a scenario starts clean.
7. **Send** — WhatsApp / SMS / call URL scheme, phone number and typed values.
8. No JavaScript errors in any run.

Changing a flow therefore requires updating `flow-behavior-spec.json` (explicit user approval, like the other locks); after that every outgoing branch of the changed screen is executed automatically.

Mutation check (run during development, all caught): skipping 3/6, adding an untested button on 4/6, removing the TPE-departure block, and the Back bug below.

Bug found and fixed by the new suite: after Scenario 1 → Call Directly, pressing Back showed Passenger Type with an empty title instead of "漏查 - 1/3" (the direct preview borrows the Final Call flow). `showScreen` now restores the owning flow for misstype / calltype / direct preview. SW cache r21.

## r22 — GitHub Actions (no computer needed)
- `.github/workflows/verify.yml` runs `verify_release.py` (including the browser flow suite) on every push / pull request, or manually via Actions → "Find Pax verify" → Run workflow. It finds the folder containing `verify_release.py` automatically.
- Result: Actions tab shows ✓ / ✗; the run's Summary page lists every FAIL line (phone-readable); the full log is kept as the `verify-output` artifact.
- `verify_release.py` SHA completeness now ignores repository/hosting plumbing: `.git*` (incl. `.github`), `.nojekyll`, `CNAME`.

## r23 — 4/6 expand + red-border timing
- 4/6 "Will protect to": the option and its CX / DEP fields now form one teal-outlined card that slides open (≈0.24 s); "Arrange in airport" glides down beneath it. Fields are white inside the card. With the keyboard open, 4/6 stays top-aligned so the page no longer re-centres and jumps.
- Red border timing (all scenarios): while typing, a field stays neutral as long as the digits can still become a valid flight (e.g. "4", "40" → 407). It turns red immediately if no allowed flight starts with the digits (e.g. "8"), when the value is complete and invalid (3 digits / 4-digit time), or when the field is left with an invalid value. Airline codes stay neutral at 1 letter until the field is left. Next-button rules unchanged.
- Old per-screen red toggles consolidated into `markInvalidFields()`; `verify_navigation.py` check updated accordingly (user-approved). Behaviour spec: +3 guards (partial typing neutral, impossible prefix red, protect panel attached to its option). SW cache r23.

## r24 — 2/6 Delayed to restyle
- "Delayed to" label enlarged (22px, brand teal, normal case) between divider lines.
- Time field: clock icon and "HH:MM" placeholder removed; the time is centred, 34px, in red (`--danger`). The field uses flex instead of the shared two-column grid, so "18:00" can never be clipped to "8:00" again.
- Footer no longer shows "HHMM" hints for Delayed to; only "Invalid time (00:00–23:59)" remains. Next rule unchanged.
- Behaviour spec +1 guard `s4_delayed_time_display` (no icon/placeholder, full 18:00 visible, red text, no HHMM hint). SW cache r24.

## r25 — Softer Delayed-to colour
- Delayed-to time colour changed from the error red (#C62828) to a muted brick red `--delay-ink: #B0574A`, weight 700, to sit with the teal palette. The error red stays reserved for red borders / invalid hints.
- Behaviour guard now checks the time uses `--delay-ink` and not the error red. SW cache r25.

## r26 — No more "jumping" between pages
Cause (measured before the fix, 390×844):
- When the keyboard opened, keyboard mode shrank the header, titles (28 → 21px) and fields (72 → 58px) and re-centred the page vertically — a moment *after* the page appeared, because the keyboard is detected once it has animated in. Titles moved up to 46px and fields up to 78px.
- The header height changed per page (76–100px) because the progress bar was removed on some pages and keyboard mode trimmed its spacing.
- Pages switched with a hard cut.

Fix (CSS only, markup unchanged):
- Form pages use one set of sizes with or without the keyboard: title 24px, fields 64px, and they stay top-aligned. Only the footer (Next button) compacts above the keyboard.
- Header is the same height on every page (progress bar space is reserved when hidden). All page titles start at the same height.
- 0.16 s fade between pages (off when the phone's "reduce motion" setting is on).
- New behaviour guard `layout_does_not_jump` measures title/field position and size with and without keyboard mode on each Scenario 4 page, plus header height across pages; it fails on the r25 layout and passes now. SW cache r26.

## r27 — 4/6 Protect-to panel (suggested design)
- Implemented the supplied `flight-arrangement` design in the app (CSS only; locked markup unchanged): "Will protect to" and its fields form one teal card; CX flight and DEP time sit **side by side** in compact 48px tinted fields (#F2F8F8, border #B5D2D5) with darker tags (#BCDADD) instead of two tall white boxes.
- Removed the small notch where the option and panel borders met.
- Narrow phones (≤360px) use tighter tag padding so "15:30" is never clipped (checked at 390 / 360 / 320px).
- Behaviour spec +1 guard `s4_protect_fields_side_by_side`. SW cache r27.

## r28 — Final Call Transit Japanese SMS (message master 1.8, user-approved)
- New copy: `【キャセイパシフィック航空】{出発地}発台北経由{目的地}行き{Flight}便は現在最終案内中です。乗り継ぎエリアで手荷物の保安検査を受けてから、至急{Gate}番搭乗口へお越しください。未検査の方は、お近くの空港スタッフへお申し出ください。現在の台北時間は{HH:mm}です。`
- Origin is derived from the flight number (`TRANSIT_SMS_ROUTE_JA`): CX451 東京, CX531 名古屋, CX565 大阪 (→香港); CX450/530/564 香港 (→東京/名古屋/大阪). City names only, so every flight is 125–126 characters = 2 SMS segments.
- No terminal is named (Gate B and C passengers can both use the T1 transfer screening).
- Chinese / English Transit copy and Join Pax copy unchanged. Locks updated: message-master 1.8, message-copy-lock and baseline-lock (`textTransit`, new constant `TRANSIT_SMS_ROUTE_JA`). Behaviour test checks the Japanese SMS for CX451. SW cache r28.

## r28 — Japanese SMS copy v1.8 (locked)
User-approved 2026-09-23. Chinese / English copy unchanged.

| Message | Japanese SMS | Length |
|---|---|---|
| S1 漏查 Join | 【キャセイパシフィック航空】お預けの荷物のX線再検査に、お客様の立ち会いが必要です。出国審査前は至急4番カウンターへ、出国審査後は搭乗ゲートのスタッフへお申し出ください。お越しいただけない場合、荷物を搭載できない可能性がございます。ご協力をお願いいたします。 | 129 (2 SMS) |
| S1 漏查 Transit | 【キャセイパシフィック航空】お預け手荷物が桃園空港の乗り継ぎX線検査を通過できませんでした。至急搭乗ゲートのスタッフへお申し出ください。 | 68 (1 SMS) |
| S2 Final Call Join | 【キャセイパシフィック航空】ご搭乗予定の{Flight}便は現在最終案内中です。搭乗締切は出発15分前です。至急{Gate}番搭乗口へお越しください。 | 68 (1 SMS) |
| S2 Final Call Transit | 【キャセイパシフィック航空】{Origin}発台北経由{Destination}行き{Flight}便は現在最終案内中です。桃園空港の乗り継ぎ保安検査場で手荷物検査を受けてから、至急{Gate}番搭乗口へお越しください。ご不明な場合は、お近くの空港スタッフへお申し出ください。現在の台北時間は{HH:mm}です。 | ≤131 (2 SMS) |

- Final Call Transit origin/destination come from the flight number (`TRANSIT_SMS_ROUTE_JA`): CX450 香港→東京, CX530 香港→名古屋, CX564 香港→大阪, CX451 東京→香港, CX531 名古屋→香港, CX565 大阪→香港. No terminal is named (Gate B and C both use the Taoyuan transfer security checkpoint).
- Locked in `message-master.json` v1.8, `message-copy-lock.json`, `baseline-lock.json` (textMiss, textMissTransit, textJoin, textTransit, TRANSIT_SMS_ROUTE_JA).
- `verify_behavior.py` now checks each Japanese SMS is **exactly** the locked copy and within its SMS length (1 or 2 segments); all six transit flights are checked with the longest gate (C1R). SW cache r28.

## r28 — Japanese SMS copy v1.9 (message master 1.9, locked)
User-approved final wording for all four Japanese SMS (Chinese/English unchanged):
1. S1 漏查 Join — 2 SMS (≤134)
2. S1 漏查 Transit — 1 SMS (≤67)
3. S2 Final Call Join — 1 SMS (≤67)
4. S2 Final Call Transit — 2 SMS (≤134); origin/destination city derived from the flight (`TRANSIT_SMS_ROUTE_JA`), screening at the Taoyuan Airport transfer security checkpoint, no terminal named.
- All open with 【キャセイパシフィック航空】. 1-SMS limit set to 67 chars as a safety margin.
- Locks updated: `message-master.json` 1.9, `message-copy-lock.json`, `baseline-lock.json`.
- Behaviour tests send each Japanese SMS and require the body to match the locked copy exactly and fit its limit — all six transit flights and the Join message with the longest gate form (C1R). SW cache r28.

## r29 — Final Call Transit Japanese v1.10 (locked)
- Gate named in the first sentence ("…便はC5番搭乗口にて最終搭乗案内中です").
- Wrong-way guidance: many Japanese transit passengers head to Taiwan immigration by mistake, so the SMS says not to enter immigration and to go back the way they came to the Taoyuan Airport transfer security checkpoint. No "Transfer" sign wording, no staff line (passengers already in Taiwan cannot make the flight).
- Max 128 chars (2 SMS). Message master 1.10; locks updated; behaviour tests check the exact text for all six transit flights. SW cache r29.


## r30 — Android startup cache-first optimization
- Changed the Service Worker runtime strategy from network-first to cache-first with background refresh for same-origin GET requests. Cached launches no longer wait for a slow or half-connected network before rendering.
- Navigation requests use the cached `index.html` immediately; the network refresh updates the r30 cache in the background. Static assets are also served from cache first and refreshed in the background.
- Removed the explicit startup `reg.update()` call and the `controllerchange` → `location.reload()` path, so an update no longer forces a second page load during an active launch. Normal Service Worker registration/update checks remain enabled with `updateViaCache: "none"`.
- UI, phone validation, message copy, navigation, and scenario behavior are unchanged. SW cache r30.


## r31 — Service Worker robustness hardening
- Preserves the r30 cache-first + background-refresh startup behavior.
- Cache write failures (for example, storage quota exhaustion) are now isolated with `cache.put(...).catch(()=>{})`, so a successful network response is still returned even if it cannot be cached.
- Navigation responses that were redirected are not written into the `index.html` runtime cache key, avoiding Chrome navigation failures caused by replaying a redirected response from Cache Storage.
- UI, phone validation, message copy, navigation, and scenario behavior are unchanged. SW cache r31.


## r32 — Disrupted Pax protect-flight validation
- Scenario 4 `Flight arrangement` → `Will protect to`: when the alternative carrier is CX, the flight number must be in the existing TPE-departure CX whitelist.
- The protected CX flight cannot be the same as `Flight from TPE`; flight numbers are compared after normalization, so leading zeroes cannot bypass the rule.
- Invalid entries use the existing red field-border + red footer-warning behavior and keep `Next` disabled. Partial CX flight prefixes remain neutral while they can still become a whitelisted flight.
- Non-CX alternative carriers keep the existing 2-character carrier + 1–3 digit flight rule. Message copy, layout, navigation, phone validation, and Service Worker runtime strategy are unchanged. SW cache r32.


## r33 — Final Call Transit confirm origin

- Final Call → 4/4 → Transit Pax → Confirm details now shows `Dep from` using the same transit-origin mapping already used by 漏查 → 3/3 → Transit Pax.
- The row is shown only for Transit Pax and is placed after `Flight` and before `Destination`.
- The phone-number home screen now shows a tiny muted `v1.1 · r33` label directly below the bottom icon so staff can confirm which release has reached the device. Release verification requires this label to match the Service Worker version/revision.
- Existing message copy, navigation, validation, and r31/r32 Service Worker cache-first behavior are unchanged. SW cache r33.


## r34 — faster first paint + home version placement

- The phone-number home screen no longer waits for `libphonenumber-max.js`: the app shell renders first, then the local phone library is loaded asynchronously after the first paint. Phone validation stays disabled (without a false invalid warning) until the library is ready, then the current input is revalidated automatically.
- Removed the redundant load-time second `clearFields() + render()` pass; startup now clears once and `showScreen("phone")` performs the single initial render.
- Service Worker cache-first/background-refresh strategy is unchanged; only the cache revision advances to r34.
- Home layout restores the r32 icon-to-Next geometry, removes the home-only footer divider, and shows only `r34` beside the icon's right foot without consuming layout height.

## r35 — Scenario 1 Join Japanese SMS copy

- User-approved change: Scenario 1 → Join Pax → Japanese SMS copy updated exactly to the approved wording.
- Chinese/English and Scenario 1 Transit copy are unchanged.
- All Scenario 2/3/4 behavior and copy are unchanged.
- Golden visual/layout/transition baseline remains unchanged; only the visible revision label changes from `r34` to `r35` without changing its geometry.
- Service Worker strategy is unchanged; cache revision bumped to `r35` only.
- Message master bumped to v1.11 and the explicitly affected copy locks were regenerated.

## r36 — Final Call Transit Japanese SMS

- User-approved change: Scenario 2 → Final Call → Transit Pax → Japanese SMS template updated.
- Dynamic Flight / origin city / destination city / Gate / current Taipei time remain automatic.
- Representative CX450 / B7 / 02:02 message is 133 Unicode characters, within the project's locked <=134-character 2-SMS target.
- All other message copy, behavior, layout, transitions, validation, navigation and PWA strategy remain unchanged from the Golden Baseline/r35 except required release identity and affected lock metadata.

## r37 — Installed PWA update check

- Authorized scope: PWA update lifecycle only.
- Service Worker registration/update check now starts immediately when the bottom script executes instead of waiting for the window `load` event.
- Cached launch remains cache-first and does not wait for network.
- Existing `skipWaiting()` / `clients.claim()` behavior is retained; no `controllerchange -> location.reload()` was added.
- Service Worker fetch/cache strategy is otherwise unchanged; CACHE_REV advanced to r37.
- No Scenario, message, validation, navigation, visual geometry or transition behavior was intentionally changed.

## r38 — Scenario 1 Join English message

- User-approved change: Scenario 1 → Join Pax → English message replaced exactly with the approved wording.
- Existing dynamic flight/SEC tag behavior remains unchanged.
- Scenario 1 Chinese/Japanese and Transit copy remain unchanged.
- Scenario 2/3/4, r37 PWA update lifecycle, validation, navigation, visual geometry and transitions remain unchanged.
