# PLAN — approved phases 2 and 3

Every item here is already approved by the user. Do a phase only when the user asks for it, one phase per conversation. Delete this file at the end of phase 3.

## Temporary lock authorization (phases 2 and 3 only)

A lock may be recomputed without asking when the change is proven output-identical:

- Messages: byte-identical for every scenario × language × passenger type × flight × gate/status combination.
- Screens: pixel-identical screenshots of every screen at 390 / 360 / 320 px, before vs after.
- Colours: identical computed colour for every element on every screen.

Any difference: stop and ask. List every recomputed lock in the handoff with its proof. The intended changes below (landline rejection, icon compression, version labels) are approved on their own and are listed separately in the handoff. This authorization ends when phase 3 is final.

## Phase 2 — colours and copy (label K1.1, `CACHE_REV` "K1.1-r1")

1. **Colours.** Every colour in `app.css`, plus the two SVG colours in `index.html` (`#AF9876`, `#04515A`), becomes a CSS variable in `:root`. The approved list in `locks.json` stays the same. After this, colour values may appear only in `:root` (and the manifest); add that check to `verify_changed.py`.
2. **copy.js** (new deployed file, loaded before `app.js`, added to `sw.js` ASSETS). Holds all message templates, progress titles, hints and errors, and rule data: general CX whitelist, transit flights, CX450/530/564 non-TPE list, SEC maximum 580, gate rules, origin/destination maps, `TRANSIT_SMS_ROUTE_JA`. Every entry has a stable ID, e.g. `s2.transit.zh`, `hint.flight.digits`, `rules.cx.general`.
   - `scenario-config.js` is merged into `copy.js` (one source for copy).
   - `message-master.json` is retired. `locks.json` keeps one hash per copy ID, so a copy change still needs approval. `verify_behavior.py` keeps checking the generated messages (placeholders, routing, SMS length); its expected copy comes from `copy.js`, whose content the hashes protect.
   - Version history is not carried over.
3. **app.js cleanup.** Remove the six history comments, the old-library fallback inside `validatePhone` (the bundled library always has `isValid()`), and the `fp-order` localStorage cleanup line. Add section markers such as `// ==== [phone validation] ====` and list them in `AI-GUIDE.md`.
4. **app.css cleanup.** Remove the seven unused classes (`bagInline`, `callNoMessageSeg`, `disruptedTitle`, `smsCta`, `transitIata`, `transitIataLabel`, `transitIataValue`) after a browser check confirms no screen uses them. Rewrite the nine history comments.
5. **Verifiers.** Empty `KNOWN_HISTORY_COMMENTS` and `KNOWN_UNUSED_CSS` in `verify_changed.py`. Add: no Chinese/Japanese string literals in `app.js`; every copy ID is used and every referenced ID exists.
6. **Docs.** Update `AI-GUIDE.md` (Where to edit → `copy.js`, section markers), README Files and §10.
7. **Release.** Label `K1.1`, `CACHE_REV` "K1.1-r1", the `CACHE_REV` check in `verify_release.py`. Run `--fast`, then `--full`.

## Phase 3 — phone library and icons (label K1.2, `CACHE_REV` "K1.2-r1")

1. **Phone library.** Replace `libphonenumber-max.js` with libphonenumber-js 1.12.29 `bundle/libphonenumber-mobile.js`, saved as `libphonenumber-mobile.js` (193,372 bytes). Update the preload link, the loader in `app.js`, `sw.js` ASSETS, and the library checks in `verify_release.py`. All 245 regions stay. The Japan branch is unchanged (it does not use the library).
   - Measured before approval: 245/245 example mobile numbers valid in both builds; formatting, detected country and E.164 output identical. Only landlines change (rejected).
   - Add to README §2: "**Landline numbers must be rejected (user-approved).** Only mobile numbers pass validation, in every country. The app uses the libphonenumber-js mobile metadata (`libphonenumber-mobile.js`); do not switch back to max/min metadata without explicit approval. Japan keeps its own rule (90/80/70/60 only), independent of the library."
   - Fixed test numbers in the priority gate. Must fail (red border, Next disabled): +886 2 2345 6789, +852 2123 4567, +81 3 1234 5678, +81 120 123 456. Must pass: +886 912 345 678, +852 9123 4567, +81 90 1234 5678, +81 60 1234 5678, +1 202 555 0123, +44 7911 123456. `verify_changed.py` runs the same list in Node when the library file changes.
   - A rejected landline shows the normal invalid state; the app cannot tell a landline from a typo.
2. **Icons.** Convert `icon-maskable-512.png` to a 64-colour palette PNG (about 13 KB); show old and new side by side to the user before replacing. Delete `icon-maskable-192.png`; the manifest keeps one maskable entry (512). Update `sw.js` ASSETS and the manifest/asset/maskable checks in `verify_release.py`. `apple-touch-icon.png` and `phone-bottom-icon.png` stay.
3. **Release.** Label `K1.2`, `CACHE_REV` "K1.2-r1". Run `--fast`, then `--full`.
4. **Finish.** Delete `PLAN.md`; remove it from `CONTROL_FILES` and `SIZE_LIMITS` in `verify_changed.py`; remove the temporary-exception sentence from README §11; update README Files.

## Expected result

Total about 540 KB (from 708 KB). A copy edit reads `AI-GUIDE.md` plus a few lines of `copy.js`: under 10 KB.
