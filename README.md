# Find Pax K2.0

Product rules for Find Pax. How to work on the code (where to edit, how to verify, how to hand over) is in `AI-GUIDE.md`.

## Files

Deployed (listed in `sw.js` ASSETS, plus `sw.js` itself): `index.html` (screen shell, layout-locked), `app.css` (all styling and colour variables), `copy.js` (all user-facing copy plus approved rule data), `app.js` (state, validation and navigation), `manifest.webmanifest`, `libphonenumber-mobile.js`, and the PNG icons.

Control (not deployed): `AI-GUIDE.md`, `README.md`, `locks.json` (hashes and approved values, read only by the verifiers), `flow-behavior-spec.json` (every screen, button and branch the browser test executes), `verify_changed.py`, `verify_release.py`, `verify_behavior.py`, `SHA256SUMS.txt` (written by the verifier after a passing check).

## Maintenance principles

- **One rule, one place.** Product rules live here. Copy and approved rule data live in `copy.js`. Hashes live in `locks.json`. Flows live in `flow-behavior-spec.json`. Code comments describe current behaviour only. History lives in the change log below and in git.
- **Edit boundaries.** Copy-only request: do not touch CSS. Logic request: do not change colours, spacing, font sizes or unrelated markup. Visual change: `app.css` only when explicitly asked, reusing existing colour tokens. `index.html` is a stable shell; do not move fields or screens for text or logic work. Any deployed file change keeps `sw.js` ASSETS and `CACHE_REV` in sync.
- **Older Android first.** No framework, build step, web font, optional chaining, native `replaceChildren()`, or unnecessary animation.
- **Surgical changes.** Anything not explicitly requested is locked. A failing lock outside the requested change is a regression, not something to re-hash.

## Privacy and safety (locked)

Find Pax handles passenger phone numbers, so these rules are locked like the layout and message copy:

1. **Staff send every message by hand.** The app only opens WhatsApp or SMS with the number and text filled in, and only after a staff tap on Confirm details. It never sends, schedules or repeats a message by itself.
2. **Nothing is kept.** No phone number, message or case history is stored between uses; every launch starts blank. No storage, cookies or databases.
3. **No server.** The app contacts no website. The only network use is the Service Worker loading the app's own files.
4. **Only three ways out:** `whatsapp://send`, `https://wa.me/` and `sms:`. No other links, external scripts, fonts, images, analytics or generated code.

Enforced four ways: the privacy lock in `verify_changed.py` (every edit); `locks.json` "privacy", which pins that lock, the phone library (official libphonenumber-js 1.12.29 mobile bundle) and `sw.js` so none can change quietly; a Content-Security-Policy in `index.html`, so the phone's browser itself refuses any other site, external file or generated code; and a run-time check in the priority gate (nothing stored, nothing loaded from another site, CSP blocking). Changing any of these rules needs explicit user approval as its own task, never as part of another change.

## Test environment limits

- Only Chromium is available. The no-Static-Routing path (iOS Safari / older Chrome) is emulated in Chromium; real Safari and real devices are not tested.
- Without Static Routing, a deployed update appears after GitHub Pages' HTTP cache (max-age 600 s) expires, on the next launch.

## Regression checklist

### 1. Startup / PWA / home screen

- Home UI renders before `libphonenumber-mobile.js` finishes loading; the library is local, precached, preloaded, and retried (bounded) if Android delays or drops the load.
- Phone validation must not show a false Invalid state while the library is loading; once it loads, the current input, country badge and Next state are revalidated.
- Startup performs one initial clear/render path only.
- Service Worker: cache-first. Launch makes zero network requests in every browser; only a cache miss goes to the network.
- Launch assets are served through Static Routing (`addRoutes()`) where supported; other browsers use the cache-first fetch handler.
- Background revalidation runs in parallel in the phone-input idle window (~600 ms after `load`), never during first paint. Unchanged files cost only a 304.
- A failed `cache.put()` must not fail a successful network response. Redirected navigation responses are never cached.
- No startup `reg.update()` and no `controllerchange -> location.reload()`. A new version takes effect on the next launch.
- Home icon-to-Next geometry is fixed (67 px gap in the reference viewport), measured at 390 / 360 / 320 px. Home divider is visually hidden.
- The release label (currently `K2.0`) sits beside the icon's right foot, takes no layout height, and matches `CACHE_REV` in `sw.js`.
- Home Scenario cards do not rely on CSS Grid / flex-gap for icon → text → arrow spacing.
- Icons: `icon-maskable-*` must never be merged with `icon-*`. Maskable icons keep the safe-zone padding that Android crops to a circle or rounded square; plain icons have none and would be cut.

### 2. Phone validation

- Invalid phone blocks Next. Canned/blocked numbers show `罐頭號碼 無用`.
- **Landline numbers must be rejected (user-approved).** Only mobile numbers pass validation, in every country. The app uses the libphonenumber-js mobile metadata (`libphonenumber-mobile.js`); do not switch back to max/min metadata without explicit approval. Japan keeps its own rule (90/80/70/60 only), independent of the library.
- Valid numbers normalize to canonical E.164 digits without `+` (`PhoneNumber.isValid()` required).
- Japan +81 has its own rule, independent of the library: after 81 and up to three tolerated leading zeroes, a 10-digit mobile part starting 90 / 80 / 70 / 60. Japanese 020, 050, 0800, landlines and wrong lengths are rejected.
- Header phone number: muted grey, grouped the way each country writes it (+886 983 952 902). Grouping is display-only; WhatsApp / SMS / call links use plain digits.

### 3. Navigation / state

- Browser Back and Forward restore the correct screen and state.
- Back/Next inside a flow preserves entered values; re-entering a scenario from the Scenario page starts a clean case, including stale red borders.
- Changing Passenger Type clears the previous type's fields; reselecting the same type after Back preserves them.
- No step count, progress title, route, control order or screen order changes unless explicitly requested.

### 4. Shared UI

- **Scenario page order:** 漏查, Final Call, Call Directly, Disrupted Passenger, Wrong Pick-Up (no numbers). Progress titles stay `Disrupted Pax - …` / `Wrong Pick-up - …`.
- **Call Directly** is its own Scenario entry, progress `Call Directly 1/1`, WhatsApp call-only, no message.
- **Icon policy:** action icons appear only on the Scenario 1/2 Passenger Type pages (single-colour message icon beside the arrow; screen readers still hear "& Message"). Every other screen is icon-free.
- **Confirm details Sec:** when the origin prefix is not TPE (Transit: HKG / NRT / NGO / KIX), the three letters use `--brand`; the digits and a TPE prefix keep the normal value colour. Not red: a different origin is not a disruption.
- **Button text colours:** option buttons use `--brand-strong` (the `.opt` default, because `button` inherits the body ink otherwise); the original delayed/cancelled flight uses `--delay-ink`; Next is `--on-brand` on `--brand`; secondary text uses `--muted`. Body ink (`--ink`) and black are never used for button text. The priority gate checks every button on every screen.
- **Confirm details colours:** a Sec whose origin is not TPE shows the three-letter prefix in `--brand`; TPE and the digits keep the value colour. The gate row (Final Call `Go to Gate`, Already at Gate `Proceed to Gate`) uses the same `--brand`. Neither is red: nothing is delayed.
- **Auto-advance:** a complete, valid field moves the cursor to the next empty field without scrolling: Protect to flight → DEP → Gate; Flight arrangement flight → dep time; airline code → number (Connecting flight, Flight arrangement, Bag 1/2); Disrupted flight → Delayed-to. An invalid value keeps the cursor.
- **Message Preview is read-only:** no in-app Edit or Copy Text.
- **Progress label:** 20px / 700, single line, auto-shrinks to min 13px (ellipsis only as a last resort); the numeric part (`2/4`) is a lighter grey-green.
- **No layout jump:** form pages keep the same sizes with or without the keyboard (title 24px, fields 64px; top-aligned except the single-field pages below); only the footer compacts. Header height is identical on every page. 0.16 s page fade, off with "reduce motion".
- **Single-field pages sit lower:** Flight number (漏查, Final Call, Wrong Pick-up), Sec, Gate, Bag Tag 1/2, Connecting flight and Arrive airport before get `padding-top: clamp(0px, (resting height − 640px) × 0.65, 180px)` (18 px on small phones, ~132 px on 844 px phones, 180 px max). The resting height is kept by `app.js` (`--rest-h`), so the page never moves when the keyboard opens, and the field stays above Next with normal and 40 px taller keyboards on 360–430 px phones. Other pages stay top-aligned.
- **Red borders:** blank fields stay neutral; a field stays neutral while its digits can still become valid (e.g. `4`, `40` → 407) and turns red when no valid value can start that way, when complete and invalid, or on leaving the field. Error red (`--danger`) is for invalid state only.
- **Gate inputs:** numeric keyboard. Area B + gate `1` shows a reserved-height `B1R?` toggle (switches B1/B1R without closing the keyboard); area C never offers B1R.

### 5. Scenario 1 — 漏查

Flow: Passenger Type -> Flight -> SEC -> Confirm details (3/3).

- Passenger types: **Joining Passenger** (big card) / **Transit Passenger**; labels come from `copy.js`.
- Join: general CX whitelist. Transit: only CX450 / 451 / 530 / 531 / 564 / 565.
- SEC is one inline field `[ IATA | SEC ]`, above 580 rejected. Join uses TPE; Transit origin: CX450/530/564 → HKG, CX451 → NRT, CX531 → NGO, CX565 → KIX.
- Transit Confirm details includes `Dep from`. Join message suffix format `450/000`.
- Languages: 中文 / English / 日本語 (Japanese = native SMS).
- Joining Confirm details (中文 / English) uses the short message only; there is no message-length control.

### 6. Scenario 2 — Final Call

Flow: Passenger Type -> Flight -> SEC -> Gate -> Confirm details (5/5). SEC follows the Scenario 1 format: origin prefix + 1–3 digit SEC, up to 580. On Confirm details, Sec appears immediately above Go to Gate. The selected flight and passenger type determine the origin prefix.

- Same passenger types and flight rules as Scenario 1.
- Gate pages (Final Call and Protect to): area and number are centred as a pair.
- Transit Confirm details includes `Dep from`; Destination shows CX450 → NRT, CX564 → KIX, CX530 → NGO, CX451 / 565 / 531 → HKG.
- Languages: 中文 / English / 日本語 (Japanese = native SMS; only Transit Japanese includes Taipei time).

### 7. Scenario 3 — Wrong Pick-up

Flow: Arrival Flight -> Bag 1 -> Bag 2 -> Confirm details (4/4).

- Arrival Flight is 1–3 digits, outside the CX whitelist. Bag tags: six digits with the airline-letter validation.
- Languages: 中文 / English only, via WhatsApp (photo sharing).

### 8. Scenario 4 — Disrupted Pax

Step 1 **Passenger Type** (1/6, no footer/Next; a choice opens the next step directly). Group **At Gate**: Already at Gate. Group **Not at the Airport**: Tight Connection, then Delayed | Suspended.

- **Main flow (6 steps):** Passenger Type -> Flight from TPE -> Connecting flight -> Flight arrangement (no visible page title; its height is kept) -> Arrival time -> Confirm details.
- **Already at Gate (5 steps):** Passenger Type -> Flight from TPE + status Delayed/Cancelled (2/5) -> Protect to (3/5) -> Proceed to Gate: original/new flight & ASAP / Wait for Staff (4/5) -> Confirm details (5/5).
- **Flight from TPE:** general CX whitelist minus CX450 / 530 / 564 (not TPE departures).
- **Delayed to:** only for Delayed, HHMM → HH:MM, 00:00–23:59, centred in `--delay-ink` (not error red), never clipped.
- **Connecting flight:** two-character alphanumeric airline code (non-CX allowed); a CX TPE departure is rejected.
- **Protect to / Will protect to:** CX must be a TPE departure and must not equal Flight from TPE (compared after normalization). Non-CX uses the airline-code rule. CX flight and DEP time sit side by side in one teal card; on Protect to (3/5) the `Protect to` title sits inside that card (no radio dot) and the Gate field sits below it under a plain centred `Gate` title. A complete DEP time moves the cursor to an empty Gate number without scrolling.
- Default message order: English first.

### 9. General CX whitelist

CX407, CX489, CX477, CX499, CX461, CX450, CX564, CX530, CX495, CX443, CX421, CX473, CX565, CX451, CX531, CX479, CX469, CX463, CX465, CX401, CX403.

### 10. Message copy

- `copy.js` is the single source for approved message templates, progress titles, hints/errors, passenger labels and shared rule data. Every stable copy ID is hash-locked in `locks.json`; never rewrite, tidy, translate, re-punctuate or rename approved copy as a side effect of another change.
- Japanese SMS: native SMS (iOS `&body=`, Android `?body=`); every message starts with 【キャセイパシフィック航空】; 1 SMS ≤ 67 chars, 2 SMS ≤ 134 chars, checked with the longest gate (C1R); no `cx/SEC/date` suffix; no terminal named.
- Only Final Call Transit Japanese appends Taipei time (`Asia/Taipei`, 24-hour `HH:mm`); origin/destination cities come from `TRANSIT_SMS_ROUTE_JA`.

### 11. Change control

1. Start from the latest user-approved ZIP.
2. Write down the exact requested change before editing.
3. Never edit `locks.json` to make a check pass. If a lock fails outside the requested change, stop and report it.
4. A lock may be recomputed only after the user explicitly approves that specific change.
5. Never report an unexecuted test as PASS.

## Change log

Only the latest two final releases. Trials are not recorded. Older history is in git.

### K2.0-r26 (2026-09-28)

- Release label is now `K2.0`.
- 漏查 Joining `s1.join.en` drops "Depending on the inspection,"; `s1.join.zh` is unchanged. Copy lock for `s1.join.en` updated.
- Service worker tests check the current `s1.join.en` text from `copy.js` instead of fixed strings.

### K1.3-r24 (2026-09-28)

- 漏查 Joining Confirm details no longer has Msg length (Short / Full). `s1.join.zh` and `s1.join.en` now hold the short message; `s1.join.zh.short`, `s1.join.en.short` and `label.preview.msgLength` are removed. s-preview layout lock, copy locks and flow tests updated.
