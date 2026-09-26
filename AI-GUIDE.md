# AI guide — Find Pax (read this first)

Do not read `locks.json`, `SHA256SUMS.txt`, the `verify_*.py` files, or all of `app.js`. Search for the name you need and read only that part. Read `README.md` only when a task touches behaviour or layout rules.

## Where to edit

| Task | Edit |
|---|---|
| User-facing copy, passenger labels, progress titles, hints/errors, approved rule data | `copy.js` (lock change: ask the user unless already approved) |
| Validation, flow, navigation | `app.js` (search the section/function name) |
| Visual change, only if asked | `app.css`, existing colour variables only |
| Screen structure | `index.html` (layout-locked: ask the user) |
| Deployed file added or renamed | `sw.js` ASSETS + bump `CACHE_REV` |

## app.js section markers

Search these markers instead of reading the whole file: `[phone validation]`, `[state]`, `[flow definitions]`, `[field validation]`, `[flight and gate rules]`, `[hints and validation messages]`, `[message generation]`, `[message draft state]`, `[render]`, `[event wiring]`.

## Workflow

1. Start from the latest approved ZIP. One task per change; never mix a feature with cleanup.
2. Make small targeted edits. Do not reformat or tidy code you were not asked to touch.
3. After each edit: `python3 verify_changed.py` (seconds, no browser).
4. Before handing over: `python3 verify_release.py --fast`. Use `--full` only when the user asks for a release (完整檢查).
5. Never edit `locks.json` to make a check pass. If a lock fails outside the task, stop and report it.
6. `PLAN.md` holds approved future phases. Follow it only when the user asks for that phase.

## Rules that keep the project small

- Trial builds: no change-log entry and no README rule change. When the user says a build is final, add one change-log entry and keep only two.
- Comments describe current behaviour. No `rNN`, `v1.x`, dates or "formerly" (verify_changed fails on them).
- New colour, new file, bigger README: verify_changed fails. Ask the user instead of working around it.
- Copy IDs are stable and hash-locked. Do not rename an ID or change its value as a side effect.
- New field or rule: label/hint copy in `copy.js`, `app.js` rule + OK/HINT, a guard in `flow-behavior-spec.json`, a test value in `verify_behavior.py`, and one README line if it is a rule.

## Handoff (five lines at most)

```
Changed: <what, in one line>
Files: <list>
Locks recomputed: none | <which, why, proof>
Check: FAST PASS <n> checks
Needs your decision: none | <question>
```

## 給使用者：下指令範本

每個任務開一個新對話，附上最新定案的 ZIP，一次一件事：

- 改文字：「S2 Final Call Transit 中文訊息改成：……」
- 改規則：「S4 Protect to 也接受 CX407」
- 定案：「這版定案」（AI 會寫一筆 change log）
- 正式發布：「完整檢查」
