# Development Progress

## 2026-10-06 — optional Trigger.dev worker checkpoint

- Added an optional Trigger.dev v4 worker scaffold alongside the Python/SQLite corpus tooling; it does not replace or complete the Private AI product runtime.
- Tasks: read-only local health inspection; bounded parser continuation only in Trigger development with local scratch/parser prerequisites; optional Anthropic `chat.agent`; and a deliberately failure-injecting retry probe. No browser/media build extensions, external secret synchronization, frontend/Realtime wiring, or CI deployment workflow is needed or configured.
- Aligned the retry probe to `ctx.attempt.number`; added generic `uiMessageStreamOptions.onError` sanitization to chat. `npm run typecheck` passes after both changes.
- Official `init --yes --project-ref proj_ldxacbqsdsakdqozeqdi` confirmed the existing project is already initialized and retrieved the logged-in account; no config override was used. Installed official OpenCode project MCP in `opencode.json`, dev-only and project-scoped. Added five focused task safety tests (`npm run test:trigger`: 5/5) and verified typecheck.
- `npx trigger.dev@latest dev`, `dev start --skip-mcp-install`, and final debug startup with skip-update/notifications all timed out in the foreground (45/90 sec) without logs; native background process support is absent and a `nohup` child did not persist. Worker readiness, task registration/run, retry/restart, and MCP connection remain unverified. No deployment, env CLI operation, corpus task, or retry-probe execution was performed.
- Safety boundary: corpus and SQLite remain local; remote execution must not be used to access private corpus paths. Keep local SSD/scratch prerequisites and fail-closed behavior. Trigger UI chat has no application auth/transport/frontend integration or product transcript persistence here.

## 2026-10-06 08:59 UTC — additive extraction recovery and terminal reconciliation

- Reconciled `repo/new/`: all 68 regular source paths match the manifest and have terminal extraction jobs: 58 VERIFIED and 10 FAILED closed; none pending or in progress. The scheduler fix allowed paused REPO-0410 and REPO-0411 to resume to VERIFIED; REPO-0419 failed closed on non-canonical archive path.
- Independently verified REPO-0410/0411: raw archive hashes, 8,324 member SHA/size values, extraction metadata, global rows, and per-repository rows all match; zero issues. Earlier REPO-0412/0413/0418 independently audited 495 member outputs. No source payload executed.
- Global extraction: 365 jobs (265 VERIFIED, 37 BLOCKED, 63 FAILED), 230,785 output rows; integrity `ok`, foreign key check 0. All ten new-subset refusals remain fail-closed.
- SSD: 936,331,341 bytes used of the 20 GiB cap; free bytes 31,443,644,416 at 08:59 UTC. Actual SSD write test is part of every new batch.
- Full test suite 57/57; focused extraction/new-batch tests 37/37; Python compilation checks pass. Existing non-failing SQLite ResourceWarnings remain.
- Parser: 68,968 rows, outbox 0; 230,785 outputs now exist. Simple missing parser-row SQL count is 161,817; 55,970 Markdown files; full provenance-aware reconciliation and Markdown audit still due. One bounded batch selected 1,000 with no errors (747 PARSED); five sampled records verify without issues.
- Project still lacks product runtime/research/memory/models/agents/UI/deployment; no completion claim.

## 2026-10-06 08:53 UTC — live extraction worker fixes

- Reconciled `repo/new/`: 68 regular source files match 68 manifest entries. The global database now has a job row for every new source: 56 VERIFIED, 9 FAILED closed, 3 resumable IN_PROGRESS records with no active lease. Global extraction totals are 365 jobs/222,461 outputs.
- Fixed `scripts/corpus_new_batch.py` lease-state selection and starvation-aware queue priority. Fresh inputs now run before paused large archives; active lease rows no longer get misreported as PAUSED. New tests cover both paths.
- Independently verified REPO-0412/0413/0418: three source SHA checks and 495 member SHA/size checks; metadata, global member rows, and per-item member rows match exactly. Zero issues. REPO-0417 remains a recorded safe symlink refusal.
- Verification: full unit suite 57/57, focused extractor/new-batch 37/37, all Python scripts/tests compile; global SQLite integrity/FK checks pass. Existing non-failing ResourceWarnings persist.
- Parser state directly reconciled: 67,968 rows, 0 outbox, 154,493 extracted outputs without current valid parser rows. No corpus completion or product-runtime claim.

The active project is documentation, control-plane and corpus tooling; there is no complete Private AI runtime/product in this root. Historical runtime is reference material and must be independently revalidated before reuse.

## 2026-10-06 verified work

- Diagnosed that Python previously used `/tmp` tmpfs: `TMPDIR`, `TEMP`, `TMP`, and `SQLITE_TMPDIR` were unset. Confirmed `/home/chris/data-processing` is device 2050, ext4 `/dev/sda2`, SSD model TS128GSSD370S (`ROTA=0`); project is device 2081, ext4 `/dev/sdc1` rotational disk (`ROTA=1`). Verified real SSD write/read/fsync/device probe.
- Added `scripts/processing_workspace.py` to route Python/SQLite temp use to SSD, verify placement, reject wrong-device production parsing, measure occupancy, check free space and enforce 20 GiB cap / 19 GiB warning / 19.5 GiB emergency thresholds.
- Integrated scratch initialization into corpus parser CLI and new-ZIP batch. New ZIP staging now reconciles filesystem/manifest names and per-file metadata instead of assuming a hard-coded 68. Its current observed input set is 68/68, independently matched.
- Additive extraction continued in bounded SSD batches. DB now has 40 VERIFIED, 5 FAILED (unsafe archive links/path collision refused), 23 PENDING without jobs, and 0 active lease. REPO-0379 `docjev-main.zip` independently verified at 687 files / 79,968,863 bytes; all source/member hashes and global/per-item output rows match. REPO-0359 was safely resumed and verified.
- Live global DB after the bounded text tranche: 198,985 extracted outputs, 67,968 current parser rows (55,223 PARSED/Markdown; 8,056 SENSITIVE; 2,964 UNSUPPORTED_TYPE; 1,543 BINARY; 161 TOO_LARGE; 21 UNSUPPORTED_ENCODING), 131,017 unparsed, outbox 0. Five new PARSED items were independently reconciled; `--verify --limit 5` found zero issues.
- Full suite `python3 -m unittest discover -s tests -q`: 54/54 passed. Python compile checks passed. All 422 managed SQLite DBs passed integrity and foreign-key checks. Existing tests emitted non-failing ResourceWarnings for unclosed SQLite connections.

Remaining: reconcile control-plane inconsistencies, finish both original/new extraction tasks, parse remaining items with full per-item mirror/Markdown reconciliation, add specialized formats, import legacy knowledge, implement research/memory/provider/agent/product runtime and perform the full audit. No completion claim is made.

**Immediate exact action:** continue the 23 pending sources using `python3 scripts/corpus_new_batch.py --project . --corpus repo --scratch /home/chris/data-processing --batch-size 12 --wall-seconds 240 --per-call-seconds 35`, then reconcile extraction results, lease state, output hashes/per-item mirrors and scratch quota.
