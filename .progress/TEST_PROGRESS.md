# Test Progress

## 2026-10-06 — progress-consistency guard added

- Added `scripts/progress_consistency.py` and `tests/test_progress_consistency.py`. The guard fails when a control-plane line presents a cumulative `stdlib-text-v3` breakdown (at least five of the six core statuses plus a total keyword) whose counts do not sum to a total stated on the same line. Batch-composition lines and historical snapshots are left alone.
- Live-database check: the corpus only grows, so the **largest** documented parser total is treated as the live claim. It must equal the live `parsed_content` row count for `stdlib-text-v3`, and the per-status counts of every line carrying that total must equal the live database counts. Historical snapshots (smaller totals) are ignored, matching the provenance convention. The database is opened read-only; `--no-database` skips this check and a missing database is skipped with a note.
- Enforced automatically across `.progress/*.md` by integration tests, so `python3 -m unittest discover -s tests -q` fails on drift. Standalone: `python3 scripts/progress_consistency.py --project .` (exit 1 on any issue). Current result: 20 files, 26 breakdowns, 0 issues; live database 85,968 rows (69,911 PARSED, 10,040 SENSITIVE, 3,596 UNSUPPORTED_TYPE, 2,220 BINARY, 179 TOO_LARGE, 22 UNSUPPORTED_ENCODING) matches the documented live total.
- The guard immediately caught a real historical drift in `SESSION_LOG.md` (stated 83,968 against a breakdown summing to 84,968); the mistyped total was corrected to 84,968.
- Full suite: `python3 -m unittest discover -s tests -q` — **70/70 passed** (was 57; +13 consistency tests). `python3 -m py_compile scripts/*.py tests/*.py` passed.
- Wired into commit and CI gates: `.githooks/pre-commit` runs the guard (enable with `npm run hooks:install`); `.github/workflows/consistency.yml` runs it plus the Python suite on push/pull request; `npm run verify` runs typecheck + guard + Python tests. No git metadata exists in the current project root, so the hook activates only once the project is initialised under git.

## 2026-10-06 — Trigger.dev

- `npm run typecheck` (`tsc --noEmit`): PASS after health output minimization, bounded continuation output minimization, chat error sanitization, and retry context correction.
- CLI init: existing project authenticated and confirmed initialized; no config override.
- `npm run test:trigger`: PASS, 5/5 pure health-status and continuation safety tests. They do not invoke Trigger runtime or corpus parser.
- Runtime test: attempted `npx trigger.dev@latest dev` (45-second timeout), `dev start --skip-mcp-install` (90-second timeout), debug startup with `--skip-update-check --skip-platform-notifications` (90-second timeout), and a further persistent foreground attempt at the tool maximum (600-second timeout). No logs before timeout; native background mode unavailable; shell-detached CLI did not persist and `.trigger/` remained empty. Worker readiness/task discovery/task run are NOT VERIFIED. MCP config installed but client connection awaits OpenCode restart. No task failure/retry/restart was tested.

Active workspace: `python3 -m py_compile scripts/corpus_inventory.py tests/test_corpus_inventory.py` passed; standard-library unittest **7/7 passed**. Tests cover stable IDs, checkpoint batching, changed-file invalidation, nested directories, symlinks, raw source immutability, output confinement, missing items, and SQLite integrity/FK status. Pytest is not detected. Next: extraction-specific positive/negative/recovery tests before processing archive payloads.
