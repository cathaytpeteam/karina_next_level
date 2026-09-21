# Find Pax v2.3.5 Hardening Notes

Date: 2026-09-22

## Changes

- Unified phone normalization into one result containing normalized digits, country, calling code, and blocked status.
- Fixed blocked-number bypass when 1–3 tolerated zeroes are inserted after the country calling code.
- Removed the hand-written country-code display table. Country is saved after libphonenumber validation and reused throughout the flow.
- Cached libphonenumber's cross-origin bundle in the Service Worker for offline use after PWA installation.
- Increased raw phone input allowance to 18 digits; normalized output is capped at 15 digits.
- Normalized flight-number fields consistently when leaving a field / advancing (leading zeroes removed).
- Added `message-master.json` SHA-256/version verification to `verify_messages.py`.
- Bumped the Service Worker app/cache version to `v2.3.5-hardening-20260922`.

## Regression checks

- JavaScript syntax: PASS
- Service Worker syntax: PASS
- Duplicate HTML IDs: 0
- Missing DOM references: 0
- Missing local assets: 0
- Message master integrity: PASS
- `textMiss`: PASS, byte-identical to original
- `textWpp`: PASS, byte-identical to original
- `textDp`: PASS, byte-identical to original
- `textCall`: PASS, byte-identical to original
- Existing PNG assets and manifest: unchanged

## Phone regression cases

- `85289648964` -> blocked
- `852089648964` -> normalized to `85289648964` -> blocked
- `8520089648964` -> normalized to `85289648964` -> blocked
- `85200089648964` -> normalized to `85289648964` -> blocked
- Shared `+7` test can preserve KZ when libphonenumber resolves Kazakhstan.

## Note on libphonenumber

The HTML continues to reference the pinned CDN version `libphonenumber-js@1.12.29`. The Service Worker now pre-caches the cross-origin response during installation and also caches opaque cross-origin responses at runtime. This improves offline reliability without changing the page's dependency version.
