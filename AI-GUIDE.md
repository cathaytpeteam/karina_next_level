# AI guide — Find Pax (read this first)

Read only what the task needs: search, then read that part. Skip `locks.json`, `SHA256SUMS.txt`, `verify_*.py`, the whole of `app.js`, and any `vb_*.py` you do not change. `README.md` only for behaviour or layout rules.

## Safety first (locked)

This app handles passenger phone numbers. Never add code that stores them, contacts a server, loads external files, runs generated code, or opens WhatsApp / SMS / the dialer without a staff tap. The one approved server call is the home Next usage count (daily report): keep it, and add or change a count only under README rule 3. If a request seems to need any of this, stop and ask. Do not touch the privacy lock, the CSP line in `index.html`, the phone library, or `sw.js` beyond `CACHE_REV` (README "Privacy and safety").

## Where to edit

| Task | Edit |
|---|---|
| User-facing text, approved rule data | `copy.js` (lock change: ask the user unless already approved) |
| Validation, flow, navigation | `app.js`, search a marker: `[phone validation]`, `[state]`, `[flow definitions]`, `[field validation]`, `[flight and gate rules]`, `[hints and validation messages]`, `[message generation]`, `[message draft state]`, `[render]`, `[event wiring]` |
| Flow or step count | `app.js`, `flow-behavior-spec.json`; with user approval, the `locks.json` navigation lock and its checks |
| Visual change, only if asked | `app.css`, existing colour variables only |
| Screen structure | `index.html` (layout-locked: ask the user) |
| Deployed file added or renamed | `sw.js` ASSETS + bump `CACHE_REV` |

## Workflow

1. Start from the latest approved ZIP. One task per change; never mix a feature with cleanup.
2. Small targeted edits; do not reformat code you were not asked to touch.
3. After each edit: `python3 verify_changed.py` (seconds, no browser). A browser test you changed: `python3 verify_behavior.py --only NAME` (seconds).
4. Before handover: `python3 verify_release.py --fast`; `--full` only when the user asks for a release (完整檢查).
5. Never edit `locks.json` to make a check pass. A lock failing outside the task: stop and report.

## Rules that keep the project small

- Trial builds: no change-log entry or README rule change. When the user says a build is final, add one change-log entry and keep only two.
- Browser tests cannot run here: write `FAST 未執行` in Check, add `-UNVERIFIED` to the ZIP name, never recommend uploading it to `main`.
- Comments describe current behaviour: no `rNN`, `v1.x`, dates or "formerly".
- New colour, new file or bigger README fails verify_changed: ask the user, do not work around it.
- Copy IDs are stable and hash-locked: never rename or change one as a side effect.
- Test files (`verify_*.py`, `vb_*.py`) are frozen: change them only when an app change needs it, a test fails wrongly, or a bug reached a real phone.
- New field or rule: copy in `copy.js`, `app.js` rule + OK/HINT, a row in `vb_validation.py`, one README line. A multi-step rule also needs a guard in `flow-behavior-spec.json` and `vb_guards_*.py`.

## Handoff (five lines at most)

```
Changed: <what, in one line>
Files: <list>
Locks recomputed: none | <which, why, proof>
Check: FAST PASS <n> checks
Needs your decision: none | <question>
```

## 給使用者：下指令範本

每個任務開一個新對話，附上最新定案的 ZIP，一次一件事。S 編號照 Scenario 頁順序：S1 漏查、S2 Final Call、S3 Call Directly、S4 Disrupted Passenger、S5 Wrong Pick-up。

- 改文字：「S2 Final Call Transit 中文訊息改成：……」
- 改規則：「S4 Protect to 也接受 CX407」
- 定案：「這版定案」（AI 會寫一筆 change log）
- 正式發布：「完整檢查」
