# Find Pax K3.0

Product rules for Find Pax. How to work on the code (where to edit, how to verify, how to hand over) is in `AI-GUIDE.md`.

## Files

Deployed (listed in `sw.js` ASSETS, plus `sw.js` itself): `index.html` (screen shell, layout-locked), `app.css` (all styling and colour variables), `copy.js` (all user-facing copy plus approved rule data), `app.js` (state, validation and navigation), `manifest.webmanifest`, `libphonenumber-mobile.js`, and the PNG icons.

Control (not deployed): `AI-GUIDE.md`, `README.md`, `locks.json` (hashes and approved values, read only by the verifiers), `flow-behavior-spec.json` (every screen, button and branch the browser test executes), `verify_changed.py`, `verify_release.py`, `verify_behavior.py` (browser-test entry) with `vb_core.py`, `vb_flows.py`, `vb_guards.py`, `vb_guards_other.py`, `vb_guards_s4.py`, `vb_priority.py`, `vb_sw.py`, `vb_validation.py` (field validation table), `SHA256SUMS.txt` (written by the verifier after a passing check).

## Maintenance principles

- **One rule, one place.** Product rules live here. Copy and approved rule data live in `copy.js`. Hashes live in `locks.json`. Flows live in `flow-behavior-spec.json`. Code comments describe current behaviour only. History lives in the change log below and in git.
- **Edit boundaries.** Copy-only request: do not touch CSS. Logic request: do not change colours, spacing, font sizes or unrelated markup. Visual change: `app.css` only when explicitly asked, reusing existing colour tokens. `index.html` is a stable shell; do not move fields or screens for text or logic work. Any deployed file change keeps `sw.js` ASSETS and `CACHE_REV` in sync.
- **Older Android first.** No framework, build step, web font, optional chaining, native `replaceChildren()`, or unnecessary animation.
- **Surgical changes.** Anything not explicitly requested is locked. A failing lock outside the requested change is a regression, not something to re-hash.

## Privacy and safety (locked)

Find Pax handles passenger phone numbers, so these rules are locked like the layout and message copy:

1. **Staff send every message and make every call by hand.** The app only opens WhatsApp or SMS with the number and text filled in, or the phone dialer with the number filled in, and only after a staff tap on Confirm details. It never sends, dials, schedules or repeats a message or call by itself.
2. **Nothing is kept.** No phone number, message or case history is stored between uses; every launch starts blank. No storage, cookies or databases.
3. **No server, apart from usage counts.** A home Next that reaches the Scenario screen, each Scenario 1 / Scenario 2 WhatsApp or Japanese SMS send tap and the Scenario 3 WhatsApp call tap on Confirm details, and each Scenario 1-3 Call by Phone tap load one image from `https://cathaytpeteam.goatcounter.com/count` carrying only one fixed name: `next`, `S1-WhatsApp`, `S2-WhatsApp`, `S1-SMS-JA`, `S2-SMS-JA`, `S3-WhatsApp Call`, `S1-Call by phone`, `S2-Call by phone` or `S3-Call by phone` (Try another number, Scenario 4 and Scenario 5 send none). No phone number, page address or referrer, and it never delays the screen change or the send. Otherwise the only network use is the Service Worker loading the app's own files. The platform comes from GoatCounter's User-Agent data, not from the app. A separate private repo (`findpax-stats`) turns these counts into three reports a day from this GoatCounter site and must count each name separately, so keep these counts, keep GoatCounter's User-Agent collection on, and update that report whenever a count is added, renamed or removed.
4. **Only four ways out:** `whatsapp://send`, `https://wa.me/`, `sms:` and `tel:`. No other links, external scripts, fonts, images, analytics or generated code; the usage-count images above are the only outside request, allowed by the CSP `img-src` for that one host.

Enforced four ways: the privacy lock in `verify_changed.py` (every edit); `locks.json` "privacy", which pins that lock, the phone library (official libphonenumber-js 1.12.29 mobile bundle) and `sw.js` so none can change quietly; a Content-Security-Policy in `index.html`, so the phone's browser itself refuses any other site, external file or generated code; and a run-time check in the safety layer, which runs first and stops every other browser check if it fails (nothing stored, nothing loaded from another site except exactly one `next` count per home Next and one fixed-name count per S1-S3 send, WhatsApp call or Call by Phone tap with no referrer, CSP blocking). Changing any of these rules needs explicit user approval as its own task, never as part of another change.

## Test environment limits

- The tests answer the usage counts locally; they never reach the real GoatCounter.
- Only under automated tests (`navigator.webdriver`) the app adds a test probe (`app.js` `[test probe]`) that answers rule and message questions for given values; it never reads the page, the case or the number. A browser check proves it is absent otherwise.
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
- **Home Clear:** a grey `Clear` chip (`--muted` text on `--surface`, `--line` border) sits right-aligned under the phone field, below the country badge. It shows while the field has a number or Try Another Number keeps a case, and its row keeps its height when hidden. One tap empties the number, badge, warning and red border, drops the kept case, and leaves the cursor in the phone field.
- Home icon-to-Next geometry is fixed (67 px gap in the reference viewport), measured at 390 / 360 / 320 px. Home divider is visually hidden.
- The release label (currently `K3.0`) sits beside the icon's right foot, takes no layout height, and matches `CACHE_REV` in `sw.js`.
- Home Scenario cards do not rely on CSS Grid / flex-gap for icon → text → arrow spacing.
- Icons: `icon-maskable-*` must never be merged with `icon-*`. Maskable icons keep the safe-zone padding that Android crops to a circle or rounded square; plain icons have none and would be cut.

### 2. Phone validation

- Invalid phone blocks Next. Canned/blocked numbers show `罐頭號碼 無用`.
- **Landline numbers must be rejected (user-approved).** Only mobile numbers pass validation, in every country. The app uses the libphonenumber-js mobile metadata (`libphonenumber-mobile.js`); do not switch back to max/min metadata without explicit approval. Japan keeps its own rule (90/80/70/60 only), independent of the library.
- Valid numbers normalize to canonical E.164 digits without `+` (`PhoneNumber.isValid()` required).
- Passengers always give a country code. Spaces, dashes, brackets and `+` are ignored, full-width digits count, and a leading `00` international prefix is dropped, so 886…, 00886… and ８８６… give the same number; the field shows the converted digits. Numbers without a country code are not guessed.
- Phone field never clips the number: the font shrinks from 24px to 18px, then the badge shows the flag only and the font may go to 16px.
- Japan +81 has its own rule, independent of the library: after 81 and up to three tolerated leading zeroes, a 10-digit mobile part starting 90 / 80 / 70 / 60. Japanese 020, 050, 0800, landlines and wrong lengths are rejected.
- Header phone number: muted grey, grouped the way each country writes it (+886 983 952 902). Grouping is display-only; WhatsApp / SMS / call links use plain digits. Shown on every screen after the phone page, Passenger Type pages and Call Directly Confirm details included.

### 3. Navigation / state

- Browser Back and Forward restore the correct screen and state.
- **Home:** the passenger number and a thin-line house icon (1.8 stroke, `--brand-strong`) share one capsule on `--scenario-bg` with no edge and no divider at the right of the header, on every screen after the phone page. The whole capsule is one button (screen readers hear "Home"); it fits beside Back at 320 px (number 14px below 360 px). One tap drops the number and the whole case, like Clear, and opens an empty phone page; it sends no usage count.
- Back/Next inside a flow preserves entered values (S4 passenger type changes clear only the delay time and Gate fields). Picking any scenario on the Scenario page clears every scenario's fields and the message, including stale red borders; the only exception is re-picking the scenario kept by Try Another Number.
- Changing Passenger Type clears the previous type's fields; reselecting the same type after Back preserves them.
- No step count, progress title, route, control order or screen order changes unless explicitly requested.

### 4. Shared UI

- **Scenario page order:** 漏查, Final Call, Call Directly, Disrupted Passenger, Wrong Pick-Up (no numbers on screen). Docs, tests and copy IDs number them S1–S5 in this order. Progress titles stay `Disrupted Pax - …` / `Wrong Pick-Up - …`.
- **Call Directly (S3)** is its own Scenario entry, progress `Call Directly 1/1`, WhatsApp call-only, no message.
- **After staff return from WhatsApp / SMS:** the main button reads `Try Another Number` (S1–S5). It returns to the phone page with the number field empty; re-picking the same scenario keeps every other field, picking another scenario clears the case. The language default follows the new number's country. A new number or any edited field reaches Confirm details with the single send button again; Back and Next without changes keep both return buttons. On S1, S2, S3 and S5 a `Call by Phone` button with a solid handset icon sits above it and opens the dialer (`tel:`) with the number filled in; Call by Phone takes the primary colours and Try Another Number the secondary ones. On S4 Try Another Number is the only button and takes the primary colours.
- **Icon policy:** action icons appear only on the Scenario 1/2 Passenger Type pages (single-colour message icon beside the arrow; screen readers still hear "& Message"). Every other screen is icon-free, except the Call by Phone button and the header Home icon.
- **Confirm details Sec:** when the origin prefix is not TPE (Transit: HKG / NRT / NGO / KIX), the three letters use `--brand`; the digits and a TPE prefix keep the normal value colour. Not red: a different origin is not a disruption.
- **Button text colours:** option buttons use `--brand-strong` (the `.opt` default, because `button` inherits the body ink otherwise); the original delayed/cancelled flight uses `--delay-ink`; Next is `--on-brand` on `--brand`; secondary text uses `--muted`. Body ink (`--ink`) and black are never used for button text. The appearance layer checks every button on every screen.
- **Confirm details colours:** a Sec whose origin is not TPE shows the three-letter prefix in `--brand`; TPE and the digits keep the value colour. The gate row (Final Call `Go to Gate`, Already at Gate `Proceed to Gate`) uses the same `--brand`. Neither is red: nothing is delayed.
- **Auto-advance:** a complete, valid field moves the cursor to the next empty field without scrolling: Protect to flight → DEP → Gate; Flight arrangement flight → dep time; airline code → number (Connecting flight, Flight arrangement, Bag 1/2); Disrupted flight → Delayed-to. An invalid value keeps the cursor.
- **Message Preview is read-only:** no in-app Edit or Copy Text.
- **Message Preview row (Confirm details):** white with a `--line` edge like the summary card; title 17px bold, language order label (e.g. 中文在前) 15px/600 `--muted`, `View ▾` 17px bold.
- **Progress label:** 17px / 700, single line, auto-shrinks to min 13px (ellipsis only as a last resort); the numeric part (`2/4`) is a lighter grey-green.
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
- Languages: 中文 / English / 日本語 (Japanese = native SMS). The phone-based default language is first; picking another language does not reorder the buttons.
- Joining Confirm details (中文 / English) uses the short message only; there is no message-length control.

### 6. Scenario 2 — Final Call

Flow: Passenger Type -> Flight -> SEC -> Gate -> Confirm details (5/5). SEC follows the Scenario 1 format: origin prefix + 1–3 digit SEC, up to 580. On Confirm details, Sec appears immediately above Go to Gate. The selected flight and passenger type determine the origin prefix.

- Same passenger types and flight rules as Scenario 1.
- Gate pages (Final Call and Protect to): area and number are centred as a pair.
- Transit Confirm details includes `Dep from`; Destination shows CX450 → NRT, CX564 → KIX, CX530 → NGO, CX451 / 565 / 531 → HKG.
- Languages: 中文 / English / 日本語 (Japanese = native SMS; only Transit Japanese includes Taipei time). Button order as Scenario 1.

### 7. Scenario 4 — Disrupted Pax

Step 1 **Passenger Type** (1/6, no footer/Next; a choice opens the next step directly). Group **At Gate**: Already at Gate. Group **Not at the Airport**: Tight Connection, then Delayed | Suspended.

- **Main flow (6 steps):** Passenger Type -> Flight from TPE -> Connecting flight -> Flight arrangement (no visible page title; its height is kept) -> Arrival time -> Confirm details.
- **Already at Gate (5 steps):** Passenger Type -> Flight from TPE + status Delayed/Cancelled (2/5) -> Protect to (3/5) -> Proceed to Gate: original/new flight & ASAP / Wait for Staff (4/5) -> Confirm details (5/5).
- **Flight from TPE:** general CX whitelist minus CX450 / 530 / 564 (not TPE departures).
- **Delayed to:** only for Delayed, HHMM → HH:MM, 00:00–23:59, centred in `--delay-ink` (not error red), never clipped.
- **Connecting flight:** two-character alphanumeric airline code (non-CX allowed); a CX TPE departure is rejected.
- **Protect to / Will protect to:** CX must be a TPE departure and must not equal Flight from TPE (compared after normalization). Non-CX uses the airline-code rule. CX flight and DEP time sit side by side in one teal card; on Protect to (3/5) the `Protect to` title sits inside that card (no radio dot) and the Gate field sits below it under a plain centred `Gate` title. A complete DEP time moves the cursor to an empty Gate number without scrolling.
- Default message order: English first.

### 8. Scenario 5 — Wrong Pick-up

Flow: Arrival Flight -> Bag 1 -> Bag 2 -> Confirm details (4/4).

- Arrival Flight is 1–3 digits, outside the CX whitelist. Bag tags: six digits with the airline-letter validation.
- Languages: 中文 / English only, via WhatsApp (photo sharing).

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

### K3.0-r56 checks (2026-10-03)

- Service Worker checks wait for the worker to finish (update check sent, network quiet, no worker installing or waiting) instead of fixed pauses, with the old pauses as upper limits; `verify_release.py --full` runs the two SW modes side by side unless `--jobs` is given. SW suite about 107 s → 35 s.
- New SW checks: an update with a new `CACHE_REV` leaves only the new cache; the new worker takes over while an older page stays open (`skipWaiting`); without Static Routing a cache miss is stored by the fetch handler before the background refresh.
- Test files only: no deployed file, lock or `CACHE_REV` changed.

### K3.0-r56 (2026-10-03)

- Test probe: only under automated tests (`navigator.webdriver`) the app answers rule and message questions for given values (`[test probe]`); it never reads the page, the case or the number. A static check and a safety-layer browser check prove it is absent otherwise.
- Checks: validation rows on one path share a page and each value is cross-checked with the probe; the probe also checks every flight 1-999, time, SEC and gate on every rule, and every message branch for every allowed flight. No locks recomputed.
- `CACHE_REV` moves to `K3.0-r56`, so the app updates on phones. The home label stays `K3.0`.
