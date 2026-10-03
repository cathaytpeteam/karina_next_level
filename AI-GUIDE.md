# AI guide — Find Pax

Use this as the editing playbook. `README.md` is the product-policy index. Search first; read only the files needed for the task.

## Do not cross these boundaries

- Passenger data is never persisted. Staff must initiate every WhatsApp/SMS/call action.
- Do not alter CSP, privacy lock, `libphonenumber-mobile.js`, or Service Worker behavior unless the user explicitly approves that exact change. A deployed change may bump `CACHE_REV` as required.
- Do not edit `locks.json` to silence a failure. Unrelated lock failure = stop and report.
- Keep Android/older Chrome compatibility: no framework/build step or unnecessary modern/runtime dependency.
- One task per change; no opportunistic cleanup or reformatting.

## Where to edit

| Need | Primary file |
|---|---|
| Copy / approved message data | `copy.js` |
| Validation / state / navigation / message logic | `app.js` |
| Browser flow or branch contract | `flow-behavior-spec.json` |
| Validation cases | `vb_validation.py` |
| Visual change explicitly requested | `app.css` |
| Screen shell explicitly requested | `index.html` |
| Deployed asset list / cache revision | `sw.js` |
| Verification architecture/budget | verifier files + `verification_budget.json` |

Prefer adding a case to an existing table/runner over copying a new verifier flow. README and this guide have size budgets; put detailed rules in their authoritative source.

## Verify

After an edit:

`python3 verify_changed.py`

If a browser test was changed, run its focused `verify_behavior.py --only ...` target.

Before handoff:

`python3 verify_suite.py --fast --jobs 3`

Local certification: `python3 verify_suite.py --full --jobs 3`. Never call an unexecuted/blocked suite PASS; `BLOCKED_ENVIRONMENT` is not product failure.

## Finalization

Intermediate work does **not** update the README Change log. Only on explicit `這版定案`: record final net changes, keep the latest two entries, run FAST, and hand off a Release ZIP. Do not run FULL in the assistant environment. The user runs FULL locally; only a passing local FULL updates `SHA256SUMS.txt` and certifies the Release. Never log intermediate failures.

## Handoff

Report only: changed files, approved lock changes (if any), check result/counts, and any decision still needed.

## User command shorthand

Scenario order: S1 漏查, S2 Final Call, S3 Call Directly, S4 Disrupted Passenger, S5 Wrong Pick-up.

Examples: `S2 Final Call Transit 中文訊息改成：…` · `這版定案` · `完整檢查`.
