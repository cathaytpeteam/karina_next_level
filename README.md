# Find Pax v1.0.6

Locked production baseline / regression guard — 2026-09-22

Find Pax is a lightweight PWA for preparing passenger-contact messages for airport ground operations.

## Protected baseline

Starting with v1.0.5, future changes must be made on top of this release. Do not rebuild from an older ZIP.

The following are release-locked unless the user explicitly asks to change them:

- All production message wording for Scenarios 1–4.
- Scenario 1 Japanese-only message wording.
- Scenario 1 `日本語` mode routes to native SMS and displays `SMSを送信`.
- Scenario 1 Chinese / English continue to use WhatsApp.
- Japan +81 phone validation and normalization rules.

`baseline-lock.json` stores cryptographic hashes for the protected executable functions.
`message-master.json` is the human-readable copy master.
`verify_release.py` must pass before every future ZIP is released.

## Japan +81 phone baseline

The first phone page already shows a `+` before the input, so the user enters international digits. For Japan the input must begin with `81`. After removing `81` and 0–3 immediately following zeroes, the mobile subscriber part must be exactly 10 digits and begin with `90`, `80`, `70`, or `60`.

Examples that normalize to `+819012345678`:

- `819012345678`
- `8109012345678`
- `81009012345678`
- `810009012345678`

The same zero-tolerance logic applies to valid `80`, `70`, and `60` mobile starts. Japanese `020`, `050`, landlines such as `03` / `06`, and wrong lengths are rejected. Other countries retain the existing validation behavior.

## Message master

Production wording is controlled by `message-master.json` and protected by both `message-copy-lock.json` and `baseline-lock.json`. Japanese Scenario 1 copy is explicitly included in Message Master v1.1.

## Release check

Run `python3 verify_release.py` before every release. A release is valid only when every check prints `PASS`. If a protected hash changes unexpectedly, do not release the ZIP. Restore the v1.0.5 baseline or obtain explicit approval for that protected change and intentionally regenerate the lock.

## PWA / Offline

The app includes a Service Worker for installed-PWA use and cached operation. Phone validation depends on the bundled/cached validation dependency being available. Cache identity is v1.0.6.

## Release history

- **v1.0.5** — Locked baseline / regression guard. Adds explicit Japanese copy master, copy/function hashes, phone-validation hashes, Japanese-SMS routing guard, and release verification. No intended user-facing workflow change from v1.0.4.
- **v1.0.4** — Japan +81 mobile-only validation.
- **v1.0.3** — Scenario 1 Japanese-only SMS mode.
- **v1.0.2** — Scenario 1 SMS option.
- **v1.0.1** — WhatsApp direct-launch reliability patch.
- **v1.0** — Initial production release.

- **v1.0.6** — Explicitly approved short Japanese Scenario 1 SMS copy; Japanese SMS suffix removed. Copy is locked by the regression guard. Japan +81 mobile validation remains unchanged from v1.0.5.


## v1.0.7 Scenario 2 structure
- Scenario 2 adds Join Pax / Transit Pax / Call Directly selection.
- Join Pax uses the modified existing flow without No message.
- Transit Pax structure reserves Japanese SMS support; Japanese copy remains pending.
- Call Directly preserves the former No message call-only behavior.
- v1.0.6 locked Japanese Scenario 1 SMS copy and +81 validation remain protected.
