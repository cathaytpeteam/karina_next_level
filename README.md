# Find Pax K3.1

Find Pax is a staff-operated, offline-first PWA for passenger contact and airport handling flows. This README is the human policy/index, not a second copy of the executable specification. Editing workflow is in `AI-GUIDE.md`.

## Source of truth

Keep each rule in one place:

| Concern | Authority |
|---|---|
| User-facing text and approved message/rule data | `copy.js` |
| Runtime state, validation, navigation, message generation | `app.js` |
| Browser flow/screens/branches | `flow-behavior-spec.json` |
| Validation test matrix | `vb_validation.py` |
| Locked hashes/approved values/privacy contract | `locks.json` |
| Styling/tokens | `app.css` |
| Deployed asset/cache list | `sw.js` |
| Verification budgets/support matrix | `verification_budget.json` |
| Release orchestration/report | `verify_suite.py`, `verification_report.json` |

Deployed files are the assets listed by `sw.js` plus `sw.js` itself. README, AI guide, locks, specs, verifiers and reports are control files and are not shipped as app assets.

## Product invariants

- **Staff initiated only.** Find Pax may prepare WhatsApp, SMS or dialer links, but never sends, calls, schedules or repeats communication by itself. Staff must tap from Confirm details.
- **Nothing is kept.** No passenger number, message or case history is persisted between uses. No storage, cookies or database.
- **No app backend.** The only approved outside requests are fixed-name GoatCounter image counts for approved staff actions. They contain no phone number, page address or referrer and must never delay the action. Scenario 4/5 and Try another number send no count.
- **Only approved exits.** External navigation is limited to `whatsapp://send`, `https://wa.me/`, `sms:` and `tel:`. CSP permits app-local resources plus the single GoatCounter image host. No external scripts, fonts, generated code or other hosts.
- **Phone library is locked.** `libphonenumber-mobile.js` is the pinned mobile build. Landlines are rejected. Japan keeps its explicit +81 mobile rule. Do not replace or trim the library without explicit approval.
- **Android Chrome is primary.** Keep the app framework-free and compatible with older/low-end Android. Safari/iPhone is optional smoke coverage in the current operating environment.
- **Surgical changes.** Anything outside the requested task is locked. Never re-hash an unrelated failure to make a check pass.

Privacy enforcement is layered: static privacy lock, hash locks in `locks.json`, CSP, Service Worker checks and the safety browser layer. Any change to this privacy contract requires explicit approval as its own task.

## Core behavior

### Phone entry

Passengers provide an international country code. Spaces, punctuation, full-width digits and a leading `00` prefix are normalized. A valid number must pass the pinned mobile metadata and normalize to E.164 digits without `+`; landlines and blocked/canned numbers fail. Japan accepts only its approved mobile prefixes and lengths. The displayed number may be grouped for readability, while WhatsApp/SMS/call links use plain digits.

Home Clear removes the number, validation state and any kept case. The Home capsule on later screens also drops the number and entire case, then returns to an empty phone page. Browser Back/Forward and in-flow Back preserve state according to the flow spec; choosing a fresh scenario clears stale scenario data except the explicit Try-another-number re-entry case.

### Scenarios

Scenario IDs follow the Scenario page order:

- **S1 — 漏查:** locate/reconnect a passenger and prepare approved contact text/call actions.
- **S2 — Final Call:** final-call contact flow, including join/transit variants and approved gate/SEC logic.
- **S3 — Call Directly:** staff calling flow; no automated call.
- **S4 — Disrupted Passenger:** disrupted-flight handling, passenger type, protection/delay/gate rules and approved outcome text.
- **S5 — Wrong Pick-up:** wrong-pick-up contact flow with approved WhatsApp/call return behavior.

Exact screens, edges, required fields and branch coverage belong to `flow-behavior-spec.json` and the browser guards. Exact message text belongs to `copy.js`. Exact field/rule cases belong to `vb_validation.py`. Do not duplicate those matrices here.

### Messaging

Approved copy is locked. Do not rewrite, translate, re-punctuate or rename message IDs as a side effect. Japanese SMS uses native SMS syntax and the approved Cathay prefix; segment limits and route/time rules are verified from the authoritative data/tests rather than repeated here.

### PWA / update behavior

The app is cache-first and must launch from its own cached assets. Static Routing is used where supported; the fetch handler covers other browsers. Updates must not force an in-session reload: a new version takes effect on a later launch. `CACHE_REV`, deployed assets and release label consistency are verification responsibilities. Maskable and plain icons remain distinct.

## Change control

1. Start from the latest approved ZIP.
2. Make one requested change at a time; do not mix feature work with cleanup.
3. Do not edit `locks.json` merely to make a failure disappear. Recompute a lock only for an explicitly approved change and record why.
4. A deployed-file change must keep Service Worker assets/cache revision consistent.
5. Never report an unexecuted test as PASS. Environment-blocked is a distinct result.
6. Documentation is an index, not a duplicate spec. Add detail to the authoritative source instead of growing this README.

## Verification

Normal release entry points:

- `python3 verify_suite.py --fast --jobs 3` — handoff gate; used before creating the Release ZIP.
- `python3 verify_suite.py --full --jobs 3` — local final certification; only a passing Full refreshes `SHA256SUMS.txt`.
- `verification_report.json` — generated machine-readable result; not a deployed asset or release fingerprint input.

`verify_suite.py` integrates architecture/mutation proof, edit/static checks, browser layers, anti-bloat budgets, performance warnings, deploy hashes and environment classification. Exit status distinguishes PASS, product FAIL and `BLOCKED_ENVIRONMENT`.

The anti-bloat budget protects verifier LOC, large files, duplicate implementation windows, minimum data-driven coverage and documentation size. Coverage should grow mainly by adding data/cases to shared runners, not by copying test flows.

Automated browser tests intercept approved external WhatsApp/SMS/tel navigation in the in-memory test copy so URLs can be asserted without leaving the app document. The real-origin CSP/privacy runtime check still requires a Chromium environment that permits localhost navigation.

## Change log

Keep only the latest two final entries; git holds older history.

### K3.1 Final (2026-10-03)

- Finalized the verification architecture: shared scenario runners, mutation proof, anti-bloat/document budgets, timed reporting, and FAST handoff + local FULL certification.
- Fixed the Full-only Retry external-navigation guard so parallel Full runs remain deterministic; Android Chrome remains the primary support target.
- Product behavior, phone validation/library, approved copy and privacy contract are unchanged; deployed release changes are limited to the K3.1 version label and cache revision.

### K3.0-r56 checks (2026-10-03)

- Service Worker verification was parallelized and expanded for cache replacement, takeover and non-Static-Routing cache behavior.
- Validation/message probes cover exhaustive approved flight/time/SEC/gate rules without changing deployed product behavior.
