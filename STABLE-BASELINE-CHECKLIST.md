# Find Pax v1.1 r34 — Stable Baseline / Regression Checklist

**Baseline:** r34  
**Status:** LOCKED STABLE BASELINE  
**Rule:** Future changes must be surgical. Anything not explicitly requested by the user is treated as locked and must remain unchanged.

## Release gate

A future release is not considered safe merely because the requested feature works. It must also preserve the r34 baseline below. A failed existing lock/test is a regression unless the user explicitly approved that exact change.

## 1. Startup / PWA / home screen

- Home UI renders before `libphonenumber-max.js` finishes loading.
- `libphonenumber-max.js` remains local/offline-capable and is still precached by the Service Worker.
- Startup performs only one initial clear/render path; do not reintroduce a second `clearFields() + render()`.
- Service Worker stays cache-first with background network refresh.
- A failed `cache.put()` must not turn a successful network response into a failed request.
- Redirected navigation responses must not be written to the navigation cache key.
- Do not reintroduce startup `reg.update()` or forced `controllerchange -> location.reload()`.
- Home icon-to-Next geometry stays identical to r32/r34 (verified r34 gap: 67 px in the reference viewport).
- Home divider is visually hidden.
- Release label is only `rNN`, positioned beside the icon's right foot, and must not consume layout height.
- Phone validation must not show a false Invalid state while the phone library is still loading.
- After the phone library becomes available, the current phone input is revalidated automatically.

## 2. Phone validation

- Invalid phone blocks Next.
- Canned/blocked number warning remains `罐頭號碼 無用`.
- Valid numbers normalize to canonical E.164 digits without `+`.
- Japan +81 mobile rule remains restricted to 90 / 80 / 70 / 60 mobile prefixes and the locked zero-tolerance behavior.
- Japanese 020, 050, landlines, 0800 and wrong lengths remain rejected.
- Existing country badge and warning behavior stays unchanged.

## 3. Navigation / state preservation

- Browser Back and Forward restore the correct screen/state.
- Back/Next inside the same flow preserves entered values for correction.
- Re-entering a scenario from Scenario starts a clean case.
- Changing Passenger Type clears fields belonging to the previous type; reselecting the same type after Back preserves them.
- Enter key behavior remains unchanged.
- No step count, progress title, route, control order, or screen order may change unless explicitly requested.

## 4. Scenario 1 — 漏查

Locked flow: Passenger Type -> Flight -> SEC -> Confirm details, 3/3 for Join/Transit.

- Passenger types remain Join Pax & Message / Transit Pax & Message / Call Directly.
- Join uses the approved general CX whitelist.
- Transit accepts only CX450 / CX451 / CX530 / CX531 / CX564 / CX565.
- Transit origin mapping remains:
  - CX450 / CX530 / CX564 -> HKG
  - CX451 -> NRT
  - CX531 -> NGO
  - CX565 -> KIX
- SEC rule including the >580 guard remains unchanged.
- Confirm details for Transit includes `Dep from`.
- Chinese/English/Japanese language availability and locked message copy remain unchanged.
- Japanese route remains native SMS; Call Directly remains WhatsApp call-only/no message.

## 5. Scenario 2 — Final Call

Locked flow: Passenger Type -> Flight -> Gate -> Confirm details, 4/4 for Join/Transit. **No SEC page.**

- Passenger types remain Join Pax & Message / Transit Pax & Message / Call Directly.
- Join uses the approved general CX whitelist.
- Transit accepts only CX450 / CX451 / CX530 / CX531 / CX564 / CX565.
- Gate validation remains required.
- Transit Confirm details must include `Dep from`.
- Transit Destination confirmation codes remain:
  - CX450 -> NRT
  - CX564 -> KIX
  - CX530 -> NGO
  - CX451 / CX565 / CX531 -> HKG
- Chinese/English/Japanese behavior remains locked.
- Japanese uses native SMS; only Transit Japanese includes Taipei time.
- Call Directly remains WhatsApp call-only/no message.

## 6. Scenario 3 — Wrong Pick-up

Locked flow: Arrival Flight -> Bag 1 -> Bag 2 -> Confirm details, 4/4.

- Arrival Flight remains outside the general CX whitelist restriction.
- Baggage tag remains six digits with the existing airline-letter validation.
- Languages remain Chinese / English only.
- Existing message copy and photo-sharing/WhatsApp behavior remain unchanged.

## 7. Scenario 4 — Disrupted Pax

Locked flow: Flight Type -> Disrupted flight -> Connecting flight -> Flight arrangement -> Arrival time -> Confirm details, 6/6.

- Flight Type options remain Tight Connection / Delayed / Suspended.
- Selecting a Flight Type immediately opens step 2/6; step 1 has no footer/Next.
- Delayed time exists only on step 2 and is required/validated only for Delayed.
- Tight Connection and Suspended do not depend on delayed time.
- `Flight from TPE` uses the approved general CX whitelist.
- Connecting Flight keeps its existing exception rules, accepts valid two-character alphanumeric IATA designators, allows non-CX, and rejects the prohibited TPE-departure case.
- Flight arrangement still requires Known/Unknown choice.
- `Will protect to` keeps existing airline/time validation.
- For CX in `Will protect to`: it must be in the TPE-departure/general CX whitelist and must not equal `Flight from TPE`.
- Same-flight comparison must continue to resist equivalent formatting such as leading zeroes.
- Non-CX Protect to remains allowed under the existing airline-code rule.
- Invalid fields continue to use the existing red field/error treatment and block Next.
- Partial flight prefixes that can still become valid must not turn red prematurely.
- Arrival time validation remains unchanged.
- Existing Chinese/English copy remains unchanged.

## 8. Approved general CX whitelist

CX407, CX489, CX477, CX499, CX461, CX450, CX564, CX530, CX495, CX443, CX421, CX473, CX565, CX451, CX531, CX479, CX469, CX463, CX465, CX401, CX403.

Applies to the locked locations defined by the app, including Scenario 1 Join, Scenario 2 Join, Scenario 4 Flight from TPE, and the later-approved CX-only check for Scenario 4 Protect to. Transit special rules and other documented exceptions remain exceptions.

## 9. Message-copy protection

The executable message generators and message master are hash-locked. Do not rewrite, tidy, translate, re-punctuate, or regenerate approved copy as a side effect of another change. Scenario 1/2 Japanese SMS routing and the Taipei-time rules are also locked.

## 10. Mandatory checks before every ZIP

Run and require PASS for:

- `verify_layout.py`
- `verify_navigation.py`
- `verify_messages.py`
- `verify_release.py`
- JavaScript syntax check
- Python verifier syntax check
- ZIP integrity and SHA-256 manifest
- Static scan that every referenced local asset exists
- Service Worker asset/cache/version consistency
- Focused real-browser test for the exact feature changed
- At least one regression pass through every scenario affected by shared code

If the full browser suite cannot run because of the test environment, say so explicitly. Never report an unexecuted test as PASS.

## 11. Change-control rule

For every future request:
1. Start from the latest user-approved stable ZIP, not an older working folder.
2. Write down the exact authorized delta before editing.
3. Do not update lock hashes just to make tests pass.
4. If an existing lock fails outside the authorized delta, stop and treat it as a regression.
5. Compare changed files against the previous stable release.
6. The final handoff must state exactly which runtime files changed and which protected areas were verified unchanged.

This checklist is intentionally conservative because prior revisions suffered regressions when unrelated UI or behavior changed during otherwise small fixes.
