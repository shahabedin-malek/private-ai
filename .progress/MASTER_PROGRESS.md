# Private AI — Master Progress

**Live checkpoint:** 2026-10-06 current session. The directly reconciled state below supersedes older progress counts later in this file; old entries are retained as provenance, not live state.

## Current-session parser checkpoint (verified)

- Reconciled 2026-10-06. The previously documented total (83,968) was inconsistent with its own stated status breakdown, which already summed to **84,968**; the DB confirmed **84,968** before the newest tranche, which added 1,000 more.
- Direct SQL now shows **85,968** `stdlib-text-v3` rows: **69,911 PARSED**, **10,040 SENSITIVE**, **3,596 UNSUPPORTED_TYPE**, **2,220 BINARY**, **179 TOO_LARGE**, **22 UNSUPPORTED_ENCODING**; provenance-aware pending **144,817**; Markdown **69,911**; parse outbox **0**.
- Measured newest tranche: 850 PARSED, 98 SENSITIVE, 42 BINARY, 9 UNSUPPORTED_TYPE, 1 TOO_LARGE, **zero errors**, **60.438 s** wall time (~993 rows/min). The newest 1,000 rows (offset 84,968) independently passed extraction provenance, per-item mirror, and PARSED Markdown hash/provenance checks (zero issues).
- Global DB integrity `ok`, FK check 0; 419 repositories, 502 repository files; extraction jobs 265 VERIFIED / 37 BLOCKED / 63 FAILED; 230,785 EXTRACTED outputs.
- `python3 -m unittest discover -s tests -q`: 57/57 passed (existing non-failing SQLite ResourceWarnings); `python3 -m py_compile scripts/*.py tests/*.py` passed.
- SSD startup probe verified `/home/chris/data-processing/private-ai-tmp/tmp` on device 2050 versus project device 2081; owned usage 936,331,341 bytes (<20 GiB), NORMAL quota, 31,073,406,976 bytes free at latest measurement.
- No active corpus process observed. Overall corpus completion is not claimed. Next exact action: run another bounded parser tranche and reconcile; 144,817 outputs remain pending.
- Current Trigger.dev local worker/runtime/MCP verification remains blocked and unverified.


## Optional Trigger.dev background worker integration (2026-10-06)

- Existing npm/Node 24 Trigger.dev 4.7.2 scaffold is confirmed: project ref `proj_ldxacbqsdsakdqozeqdi`, `dirs: ["./src/trigger"]`, 900-second global ceiling, `.trigger` and env files ignored, config/tasks included in TypeScript. Official CLI init authenticated and reported the project already initialized; no config override was used.
- `npm run typecheck` passes. Exported health, progress-inspection/bounded continuation, optional chat, scheduled health, retry probe, and initializer demo tasks exist. Health results avoid local paths and git filenames; parser execution is dev-only, bounded, and default action is inspection.
- `npx trigger.dev@latest dev` and `dev start --skip-mcp-install` both exceeded the tool's 45/90-second foreground timeouts without output. Worker readiness/task discovery/execution are therefore NOT verified. Do not claim a health run succeeded. No deploy, corpus parse, retry-probe run, env pull/show, or cloud reporting was performed.
- Optional architecture details are in `docs/TRIGGER_DEV_ARCHITECTURE.md`. Official OpenCode MCP installed project-scoped with `--dev-only`; `opencode.json` target confirmed by installer. Client connection still awaits OpenCode restart/observation. Added five focused tests for health assessment and continuation guards; `npm run test:trigger` 5/5, `npm run typecheck` passes.
- Retried persistent worker startup: terminal tool rejects native background mode; `nohup` child did not persist and no `.trigger/dev.log` was retained. Foreground dev attempts timed out at 45/90 seconds without logs. Worker ready/task registration/task run remain UNVERIFIED; do not claim the primary success condition.
- This additive execution adapter does not change the active CORPUS-0006 source of truth or replace existing local workers; cloud workers must not access local corpus/SSD paths.


## Current phase and tasks

- PHASE 0 historical/machine audit: bounded and documented, not exhaustive.
- Inventory IDs/manifests/workspaces: previously established; stable IDs retained. Original inventory audit retained REPO-0159 as a source-MISSING item. Its filesystem state needs ordinary reconciliation, without renumbering.
- CORPUS-0005 current-scope reconciliation: 365/365 manifest archive candidates were checked in 37 durable batches. 364 extant sources hashed, one manifest-missing source retained; 265 extraction outputs match verified provenance, 100 terminal jobs reconciled. Four report issues remain on REPO-0154 and REPO-0329 because published directories contain 30 and 2 SQLite WAL/SHM sidecars absent from archive metadata. Sidecars are consistent with later SQLite runtime artifacts and absent in source ZIP listings, but are left untouched and flagged; no destructive repair. Historical zero-issue 297-candidate report is superseded in scope.
- CORPUS-0006 text parser: `stdlib-text-v3`, migration `corpus-parse-v4`, in progress.
- CORPUS-0006-NEW-ZIPS additive extraction: in progress.
- SSD-0001 scratch routing/quota: implemented and verified for parser/new-batch CLIs.

## Directly measured current database/filesystem state

- Global DB: 419 repositories.
- Global DB currently contains 419 repositories, 502 repository files, 365 archive candidates; extraction jobs: **365** — **265 VERIFIED**, **37 BLOCKED**, **63 FAILED**, zero IN_PROGRESS. EXTRACTED output rows: **230,785**. All 68 additive sources have terminal statuses: **58 VERIFIED**, **10 FAILED closed**; no additive item is missing a job. Original candidates still require full queue reconciliation.
- New-source filesystem `repo/new/`: **68** regular top-level files; new/ manifest: **68**; filename sets match exactly.
- New-source extraction: 68/68 raw inputs match the manifest and have terminal job rows. **58 VERIFIED**, **10 FAILED closed**, zero PENDING/IN_PROGRESS. REPO-0410/0411 resumed to VERIFIED; REPO-0419 failed closed for a non-canonical path. Independent audit of REPO-0410/0411 checked 8,324 extracted member hashes/sizes and global/per-item DB rows (zero issues); earlier audit of REPO-0412/0413/0418 checked 495 more outputs. Failures: unsafe symlink paths in REPO-0366/0374/0393/0396/0403/0416/0417, duplicate/case-collision in REPO-0387, compression ratio refusal in REPO-0384, non-canonical path in REPO-0419. Do not bypass extraction safety.
- Current parser DB at this checkpoint: **85,968** rows for `stdlib-text-v3`: **69,911 PARSED**, **10,040 SENSITIVE**, **3,596 UNSUPPORTED_TYPE**, **2,220 BINARY**, **179 TOO_LARGE**, **22 UNSUPPORTED_ENCODING**. Provenance-aware pending query finds **144,817** extracted outputs; the previous full paged audit of 82,968 persisted rows preceded the newest tranches. Outbox is **0**.
- Markdown files under `data/knowledge/files/`: **69,911**, equal to PARSED count. Complete paged audit of the previous 82,968 persisted parser rows returned zero issues; the newest 1,000 rows (offset 84,968) independently passed mirror/hash/provenance checks. Pending outputs remain unparsed.
- Global SQLite `integrity_check=ok`, `foreign_key_check` has zero issues. A prior read-only pass over all **422 managed SQLite DBs** passed; current full rescan after latest parser batch remains advisable.

## SSD verification and quota

- `/home/chris/data-processing`: ext4 `/dev/sda2`, device **2050**, SSD `TS128GSSD370S`, `ROTA=0`.
- Project data mount: ext4 `/dev/sdc1`, device **2081**, Hitachi WDC device reporting `ROTA=1`. Separate devices verified.
- Before this change, `TMPDIR`, `TEMP`, `TMP`, `SQLITE_TMPDIR`, XDG cache/state were unset and Python `tempfile.gettempdir()` was `/tmp` (tmpfs). This explains why default Python temporaries did not use the SSD.
- Added `scripts/processing_workspace.py`: process-local temp routing, private scratch directories, actual fsync/read-back/device probe, usage/free checks, 20 GiB hard maximum, 19 GiB warning and 19.5 GiB emergency severity. Parser/new-batch CLI initialization is explicit. This is not system-wide and does not prove historic runs used SSD.
- Current owned SSD staging usage: **936,331,341 bytes**; under 20 GiB cap. Free space measured about **31.07 GB** in the latest session; quota NORMAL; time-sensitive. No automatic deletion.

## Latest work and verification

- Current session: bounded SSD parser tranches of 1,000 each, zero errors. Newest measured tranche: 850 PARSED, 98 SENSITIVE, 42 BINARY, 9 UNSUPPORTED_TYPE, 1 TOO_LARGE; 60.438 s wall time.
- Direct SQL now reconciles parser rows to 85,968, pending 144,817, Markdown 69,911, outbox 0. The newest 1,000 rows (offset 84,968) passed independent provenance/mirror/Markdown validation, zero issues. Full paged audit passed for 82,968 persisted rows at the last full re-audit; 144,817 outputs remain pending. Note: the previously documented total 83,968 contradicted its own status breakdown, which summed to 84,968.
- SSD probe verified Python tempfile path `/home/chris/data-processing/private-ai-tmp/tmp` on device 2050, distinct from project device 2081; usage 936,331,341 bytes (<20 GiB), free ~31.09 GB at measurement time.
- Python full suite 57/57 passed; py_compile passed. Two pre-existing non-failing SQLite `ResourceWarning`s were emitted.
- `scripts/corpus_new_batch.py` no longer hard-codes expected input count 68; it compares filesystem names and manifest names, requires safe top-level paths and unique IDs, and verifies staged file size/hash. Current 68/68 input set reconciles.
- `scripts/corpus_parse.py` now initializes SSD and emits a verified startup diagnostic. Default production mode requires the scratch root to be on a separate device from project data; explicit `--allow-same-device` supports fixtures/degraded mode only.
- A further 1,000-output parser batch ran on verified SSD scratch: 868 PARSED, 113 SENSITIVE, 9 UNSUPPORTED_TYPE, 10 BINARY, no errors. Direct SQL confirms rows 71,968→72,968, provenance-aware pending 158,817→157,817, Markdown 58,214→59,082, outbox 0. Ten latest parsed Markdown hashes/provenance and per-item mirrors independently checked with zero issues. This batch's delta reconciles exactly; earlier timing-discrepancy cause remains unknown.
- New ZIP work advanced from 40 to 58 VERIFIED. Latest REPO-0410/0411 resumed safely; independent audit checked 8,324 members (5,072 + 3,252), raw source hashes and per-item/global output rows with zero discrepancies. REPO-0419 remained fail-closed on non-canonical path. Global DB integrity is `ok`, foreign-key check 0; no active extraction jobs remain.
- Fixed `extraction_state()` to include lease owner/expiry, so paused-vs-live task state is classified correctly. Added a regression test and starvation-aware batch ordering (unattempted work before paused large archives) so a single expensive resume cannot indefinitely starve pending sources.
- Full test suite: `python3 -m unittest discover -s tests -q` — **57/57 passed**; focused new batch/extractor tests 37/37 passed; Python compilation checks passed. Existing tests emit non-failing SQLite `ResourceWarning`s.

## Immediate exact next action

Run `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120` on the verified SSD workspace. After the batch, independently reconcile SQL parser status and pending deltas, Markdown hash/provenance, per-item mirrors, outbox/errors, integrity/FKs, and SSD usage. Continue bounded tranches; the paged audit of 80,968 persisted rows passed before the last tranche, while 144,817 extracted outputs remain pending.

The full original-candidate report `.progress/CORPUS_CURRENT_RECONCILIATION.json` checks 365/365 candidates but has four discrepancies due to runtime-like SQLite WAL/SHM sidecars in REPO-0154/0329. Leave artifacts untouched; establish provenance safely before any remediation.

## Known incomplete / limitations

- Approximately 144,817 extracted outputs remain without a valid current `stdlib-text-v3` record according to provenance-aware pending SQL; parser remains text-only and does not semantically process OCR, PDF/Office, audio/video, or AST/code symbols.
- 10 additive extraction refusals remain fail-closed for risky archive members; no pending additive jobs. Original archive queue still needs a current full reconciliation beyond the historical 297-item report.
- Historical knowledge import, research/cache/worker, persistent memory, model/provider adapters/routing, tools/MCP/A2A, agents, CLI/API/web/VS Code, voice/media, services, deployment and final audits are not implemented/verified as product features.
- Historical project review was evidence-bounded; 6.1 GiB backup archive was unopened; legacy worktree was dirty.
- Older control-plane sections below retain stale/inconsistent checkpoint figures as provenance. Trust the live checkpoint above and freshly verified database/filesystem state over old prose.

---

## Historical checkpoint log (retained; not live totals)

The following older records are retained for audit provenance. Their counts, status claims, commands, and “next actions” are superseded by the live checkpoint above where conflicting.

- On 2026-10-06 earlier parser work reported 50,317/192,186 rows; current DB now reports 67,968/198,985 after further processing/integration. Reconcile from SQLite before resuming.
- On 2026-10-05 historical CORPUS-0005 report checked 297 then-known archive candidates, zero issues: 207 VERIFIED, 37 BLOCKED, 53 FAILED plus a manifest-missing source item. This was before/additive to new repository inputs; it is not current total extraction completeness.
- Initial stable inventory record: IDs REPO-0001–REPO-0351, 351 identities including REPO-0159 which was later observed missing; old manifest totals: 434 file records and 16,820,747,697 bytes. Refresh current inventory before asserting those remain current.
