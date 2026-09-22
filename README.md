# Find Pax v1.0.1

WhatsApp launch reliability patch — 2026-09-22

Find Pax is a lightweight PWA for preparing passenger-contact messages for airport ground operations.

## Scenarios

1. 漏查
2. Call Passenger
3. Wrong Pick-up
4. Disrupted Pax

## Input rules

- Phone: international number input; validation and normalization are applied before continuing.
- Flight: CX is fixed where applicable; enter 1–3 digits. Leading zeroes are normalized.
- Gate: Zone B / C is selected separately. Gate accepts 1–9 or 1R.

## Message Master

Production message wording is controlled by `message-master.json` and protected by `message-copy-lock.json`.
Run `verify_messages.py` before release. All four executable message generators must pass verification.

## PWA / Offline

The app includes a Service Worker for installed-PWA use and cached operation. Phone validation depends on the bundled/cached validation dependency being available.

## Release

**v1.0.1 — WhatsApp launch reliability patch — 2026-09-22**

- Send WhatsApp now tries the installed WhatsApp app directly via `whatsapp://` first.
- If WhatsApp cannot be opened, the app falls back to `wa.me`.
- Service-worker cache version bumped so installed PWAs receive the fix.

**v1.0 — Initial Production Release — 2026-09-22**
