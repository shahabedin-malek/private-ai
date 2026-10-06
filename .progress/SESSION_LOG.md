# Session Log

## 2026-10-06 — corpus reconciled to measured state

- Read the live control-plane notes. The prior documented parser total (83,968) was inconsistent with its own stated status breakdown, which summed to **84,968**; a read-only DB query confirmed **84,968** before any new work.
- Pre-state (read-only): 84,968 `stdlib-text-v3` parser rows; 145,817 provenance-aware pending; Markdown 69,061; 230,785 extracted outputs; outbox 0; integrity `ok`, FK 0; no active parser/extractor process.
- Ran one bounded SSD-routed tranche with the documented command (`--limit 1000 --max-mb 2 --max-wall-seconds 120`): 1,000 selected — 850 PARSED, 98 SENSITIVE, 42 BINARY, 9 UNSUPPORTED_TYPE, 1 TOO_LARGE — **zero errors**, **60.438 s** wall time (~993 rows/min).
- Post-state: parser rows **85,968**; provenance-aware pending **144,817**; Markdown **69,911**; DB 458,936,320 bytes (+648 KB per 1,000 rows); outbox 0; integrity `ok`, FK 0.
- Reconciliation: the newest 1,000 rows (offset 84,968) passed extraction provenance, per-item mirror, and PARSED Markdown hash/provenance checks — **zero issues**. A timed `--verify --limit 1000` pass took ~1.8 s.
- SSD: device 2050 versus project device 2081; used 936,331,341 bytes (<20 GiB cap); 31,073,406,976 bytes free; quota NORMAL.
- `python3 -m unittest discover -s tests -q`: 57/57 passed (existing non-failing SQLite ResourceWarnings); `python3 -m py_compile scripts/*.py tests/*.py` passed.
- Reconciled `.progress/MASTER_PROGRESS.md`, `CURRENT_TASK.md`, `TASK_STATUS.md`, `TASK_QUEUE.md`, `CONTINUATION_PROMPT.md`, and `EFFORT_ESTIMATE.md` to the measured state. Overall completion is not claimed; 144,817 outputs remain pending and the four REPO-0154/0329 sidecar discrepancies remain untouched.

### Exact next action

Run another bounded parser tranche (`python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120`) and reconcile DB/pending/Markdown/mirror/outbox/integrity/SSD deltas; 144,817 outputs remain pending.

## 2026-10-06 — resumed bounded corpus parser and reconciled outputs

- Read the live continuation/master/current task/queue/status notes before resuming; confirmed the project root and global SQLite database exist. The existing notes had stale parser counts, so all new counts below come from direct current queries.
- Checked `/proc` for corpus parser/extraction/Trigger task processes: none active (the command's own diagnostic process also matched its search strings). Global DB opened read-only for baseline; extraction jobs: 365 (265 VERIFIED/37 BLOCKED/63 FAILED), extracted outputs 230,785, parser rows 75,968, parse outbox 0, integrity `ok`, FK check 0.
- Verified `/home/chris/data-processing` is device 2050 and durable project device 2081; workspace usage 936,331,341 bytes, below 20 GiB cap. Fresh-shell Python defaults to `/tmp` because TMPDIR/TEMP/TMP/SQLITE_TMPDIR are unset; parser CLI performs process-local SSD initialization/probe.
- Ran `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120`. Startup output verified SSD temp path/device and quota. Batch selected 1,000: 933 PARSED, 42 SENSITIVE, 16 UNSUPPORTED_TYPE, 8 BINARY, 1 TOO_LARGE; zero errors.
- Independent SQLite/filesystem reconciliation: parser rows 75,968→76,968; provenance-aware pending 154,817→153,817; Markdown 61,526→62,459; outbox 0. All 1,000 latest rows passed global extraction provenance and per-repository mirror checks; PARSED Markdown hashes/provenance verified; zero issues. Global integrity `ok`, FK 0. SSD remained 936,331,341 bytes; free space about 31.10 GB at measurement time.
- Refreshed `.progress/CONTINUATION_PROMPT.md`, `.progress/MASTER_PROGRESS.md`, and `.progress/CURRENT_TASK.md`. Overall completion is not claimed; original sidecar discrepancies and parser backlog remain.

### Exact next action

Run one bounded SSD-routed parser tranche using `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120`, then independently reconcile DB status/pending deltas, Markdown hashes/provenance, per-item mirrors, outbox, integrity/FKs, and SSD quota. Later run the paged full parser/Markdown audit and current-scope original archive reconciliation.

## 2026-10-06 — eighth parser tranche reconciled

- Ran bounded SSD-routed batch of 1,000: 830 PARSED, 168 SENSITIVE, 2 UNSUPPORTED_TYPE; zero errors.
- Direct DB: 84,968 parser rows (69,061 PARSED, 9,942 SENSITIVE, 3,587 UNSUPPORTED_TYPE, 2,178 BINARY, 178 TOO_LARGE, 22 UNSUPPORTED_ENCODING), 145,817 provenance-aware pending, Markdown 69,061, outbox 0. *(Total corrected from a mistyped 83,968; the breakdown, pending and Markdown figures already summed to 84,968.)*
- Independently audited latest 1,000 rows for extraction provenance, per-item mirror and PARSED Markdown hashes/provenance: zero issues. Global integrity `ok`, FK 0.
- Full paged parser audit now covers 82,968 rows, including the last full audit refresh plus two batches; latest 1,000-row tranche remains to include. SSD verified on device 2050, usage 936,331,341 bytes (<20 GiB), NORMAL; ~31.09 GB free at measurement.
- Project/corpus incomplete. Exact next action: run another bounded tranche and reconcile; then re-audit at suitable interval, retaining source sidecar discrepancy and fail-closed states.

## 2026-10-06 — sixth and seventh parser tranches reconciled

- Sixth SSD-routed batch of 1,000: 765 PARSED, 143 SENSITIVE, 35 UNSUPPORTED_TYPE, 57 BINARY; zero errors. Direct SQL reconciled to 81,968 parser rows, 148,817 provenance-aware pending, Markdown 66,491.
- Seventh SSD-routed batch of 1,000: 915 PARSED, 80 SENSITIVE, 2 UNSUPPORTED_TYPE, 3 BINARY; zero errors.
- Current direct DB: 82,968 parser rows (67,406 PARSED, 9,615 SENSITIVE, 3,569 UNSUPPORTED_TYPE, 2,178 BINARY, 178 TOO_LARGE, 22 UNSUPPORTED_ENCODING), 147,817 provenance-aware pending, Markdown 67,406, outbox 0.
- Independently audited the latest 1,000 rows for extraction provenance, per-item DB mirror, and PARSED Markdown hash/provenance; zero issues. Global SQLite integrity `ok`, FK 0.
- Full paged parser audit last passed for 80,968 records, before the latest two batches. Re-audit to include the newest 2,000 rows later; no full queue completion claim.
- SSD write probe verified device 2050 distinct from project 2081; usage 936,331,341 bytes, NORMAL under 20 GiB cap; about 31.09 GB free at measurement time.
- Python suite 57/57 pass and py_compile passed earlier this session; no source sidecar discrepancy was changed.

### Exact next action

Run one bounded parser tranche; independently reconcile DB/status/pending deltas, per-item mirrors, Markdown, outbox, integrity/FKs and SSD cap. Re-audit parser rows after a reasonable batch interval. Continue toward 148,817 pending outputs, then current-scope archive reconciliation.

## 2026-10-06 — fifth parser tranche and complete persisted-row re-audit

- Ran fifth bounded SSD-routed batch of 1,000: 710 PARSED, 110 SENSITIVE, 30 UNSUPPORTED_TYPE, 150 BINARY; zero errors.
- Direct DB after five batches: 80,968 parser rows (65,726 PARSED, 9,392 SENSITIVE, 3,532 UNSUPPORTED_TYPE, 2,118 BINARY, 178 TOO_LARGE, 22 UNSUPPORTED_ENCODING), 149,817 provenance-aware pending, Markdown 65,726, outbox 0.
- Independently audited latest 1,000 rows for extraction provenance, per-item DB mirror, and Markdown hash/provenance where PARSED: zero issues.
- Re-ran full paged parser audit `python3 scripts/corpus_parse.py --project . --audit --limit 1000`: all 80,968 persisted parser rows passed, zero issues. 149,817 eligible outputs still lack current parser records; this is not full queue completion.
- SSD write probe verified device 2050 distinct from project 2081; usage 936,331,341 bytes, NORMAL under 20 GiB cap; about 31.09 GB free at measurement time.
- Prior `python3 -m unittest discover -s tests -q` result remains 57/57 pass; Python compile passed. No source sidecar discrepancy was changed.

### Exact next action

Run one bounded parser tranche and reconcile output/pending deltas, per-item mirrors, Markdown, outbox, database integrity/FKs and SSD cap. Continue until all eligible outputs have terminal parser dispositions; then reconcile current original/additive archive scope.

## 2026-10-06 — four parser tranches, paged full audit, and tests

- Ran two additional SSD-routed batches of 1,000. Third batch: 816 PARSED, 76 SENSITIVE, 31 UNSUPPORTED_TYPE, 75 BINARY, 1 TOO_LARGE, 1 UNSUPPORTED_ENCODING. Fourth: 903 PARSED, 52 SENSITIVE, 21 UNSUPPORTED_TYPE, 24 BINARY. Both had zero reported errors.
- Direct DB after four batches: 79,968 parser rows (65,016 PARSED, 9,282 SENSITIVE, 3,502 UNSUPPORTED_TYPE, 1,968 BINARY, 178 TOO_LARGE, 22 UNSUPPORTED_ENCODING), 150,817 provenance-aware pending, Markdown 65,016, outbox 0.
- Independently audited latest 1,000 rows (extraction provenance and item DB mirror; Markdown hashes/provenance for PARSED) with zero issues.
- Ran full paged parser audit `python3 scripts/corpus_parse.py --project . --audit --limit 1000`: processed all 79,968 persisted parser rows, 81 pages including final short page and empty terminator, zero issues. This audits existing parser rows only; 150,817 outputs remain pending.
- Ran `python3 -m unittest discover -s tests -q`: 57/57 passed in ~2s. Two pre-existing SQLite ResourceWarnings surfaced from corpus inventory; no test failures. `python3 -m py_compile scripts/*.py tests/*.py` passed.
- Final direct reconciliation: global DB has 419 repositories, 502 repository_files, 365 extraction jobs (265 VERIFIED, 37 BLOCKED, 63 FAILED), 230,785 extracted outputs; integrity `ok`, FK 0. SSD used 936,331,341 bytes (<20 GiB), NORMAL, free ~31.09 GB at measurement time; parser temp write/device verified.
- Updated live continuation, master progress, current task, status, queue. Overall project/corpus incomplete; source-sidecar discrepancies and extraction failure states remain.

### Exact next action

Run one more bounded parser tranche: `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120`. Immediately reconcile parser counts/pending/output delta, outbox/errors, Markdown hash/provenance and item mirrors, global DB integrity/FKs, and SSD cap. Continue until parser backlog reaches zero; then run full scope reconciliation for original/additive archives.

## 2026-10-06 — second parser tranche and independent reconciliation

- Ran the same bounded parser CLI; SSD diagnostic again verified tempdir on device 2050 vs project device 2081, 936,331,341 bytes owned usage (<20 GiB), NORMAL quota.
- Batch selected 1,000: 816 PARSED, 76 SENSITIVE, 31 UNSUPPORTED_TYPE, 75 BINARY, 1 TOO_LARGE, 1 UNSUPPORTED_ENCODING; zero errors.
- Direct SQL reconciliation: parser rows 76,968→77,968; provenance-aware pending 153,817→152,817; Markdown 62,459→63,275; outbox 0.
- Independently audited all 1,000 latest rows: extraction provenance and global/per-item mirror match, plus Markdown hashes/provenance for PARSED state; zero issues. Global integrity `ok`, FK 0. SSD usage unchanged; free space about 31.09 GB at measurement time.
- Refreshed live continuation, task/status queue and master checkpoint. Still no overall corpus completion claim; original sidecar discrepancies and parser backlog remain. Full test suite not rerun this session.

### Exact next action

Run the next bounded parser tranche and independently reconcile output statuses, pending rows, per-item mirrors, Markdown hash/provenance, database integrity/FKs, outbox/errors, and SSD cap. Then schedule full paged audit and current-scope original archive reconciliation.


## 2026-10-06 — OpenCode MCP install, focused task tests, and final dev startup attempts

- Additional persistent-session retry: `npx trigger.dev@latest dev start --skip-mcp-install --skip-update-check --skip-platform-notifications` ran through the tool's 600-second limit and was terminated by the tool without output. `.trigger/` remained empty afterward, so there is still no evidence of a local worker session, task discovery, or task run.
- Revalidated after timeout: `npm run typecheck` passes; `npm run test:trigger` passes 5/5. These are code tests only, not Trigger runtime verification.

- Confirmed OpenCode project config target from official Trigger.dev SDK docs and installed CLI support; ran `npx trigger.dev@latest install-mcp --client opencode --scope project --dev-only --project-ref proj_ldxacbqsdsakdqozeqdi`. Installer wrote `opencode.json` with `--dev-only` and project ref. Restart OpenCode to establish connection; no MCP client connection was available to verify in this terminal session.
- Added Node built-in `node:test` checks for health status and continuation guards (`tests/trigger-tasks.test.ts`, `npm run test:trigger`). All five tests pass; no Trigger runtime task or corpus parser is invoked by tests.
- `npm run typecheck` passes.
- Attempted a persistent local dev session by shell-detaching `npx trigger.dev@latest dev start --skip-mcp-install` into ignored `.trigger/dev.log`; child did not persist and `.trigger` remained empty. A final foreground attempt with `--skip-mcp-install --skip-update-check --skip-platform-notifications --log-level debug` timed out at 90 seconds without output. Tool's native BACKGROUND mode is unavailable. No worker-ready signal, task discovery, task run, retry, or restart was observed; cannot claim primary runtime success.
- No API key/environment command, deployment, parser task, retry probe, cloud query, or corpus changes were performed.

### Exact next action

In a persistent terminal environment, run `npx trigger.dev@latest dev start --skip-mcp-install`, wait until the worker and `private-ai-health` task are explicitly listed, then trigger only `private-ai-health` and inspect the structured result. After that, separately verify task failure/retry/restart. Restart OpenCode to load its installed dev-only MCP config.

## 2026-10-06 — Trigger.dev scaffold audit and local-run attempt

- Audited existing files before editing: npm with `package-lock.json`; Node v24.21.0; Trigger SDK/build/CLI 4.7.2; no app framework/backend or `.github/workflows`; existing Python/SQLite corpus tooling and `.progress` controller remain core. `trigger.config.ts` already points to `proj_ldxacbqsdsakdqozeqdi`, `./src/trigger`, Node 24, global maxDuration 900; `.trigger`, env files ignored; tsconfig includes config/tasks.
- CLI `npx trigger.dev@latest init -p ...` refused non-TTY prompts and advised `--yes --project-ref`. Retried exactly as advised; CLI authenticated, retrieved account details, and reported the project already initialized. No override performed.
- Tightened `private-ai-health` output to report structured availability/space/git counts without absolute paths or changed filenames; health is degraded if required DB/progress/scratch paths are absent. Tightened continuation inspection to avoid returning persisted next-action text, and parser output now returns only booleans (not local paths/diagnostics). `parse-batch` remains development-only and bounded. Chat errors are sanitized; retry probe uses `ctx.attempt.number`.
- Created `docs/TRIGGER_DEV_ARCHITECTURE.md` and updated master/continuation/task queue/status/development progress with current verification state. Existing corpus state was not changed.
- `npm run typecheck` passes. `npx trigger.dev@latest dev` timed out after 45 seconds; `npx trigger.dev@latest dev start --skip-mcp-install` timed out after 90 seconds with no output. No evidence of worker readiness, task registration, task success/failure, retry or restart. MCP/skills remain uninstalled/unverified; no supported client config was assumed. No deploy, cloud query/report, secret/env command, parser invocation, or retry probe was run.

### Next exact action

Resume a visible persistent terminal with `npx trigger.dev@latest dev start --skip-mcp-install`, confirm worker registration and run only `private-ai-health`. Then verify failure/retry/restart separately. Do not start local corpus parsing unless actual scratch/root mounts are confirmed in that runtime.

## 2026-10-06 09:54 UTC — parser tranche reconciled

- Re-read current task and continuation checkpoint before resuming CORPUS-0006.
- Ran `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120`. Startup diagnostic verified Python tempdir `/home/chris/data-processing/private-ai-tmp/tmp`, SSD device 2050 versus project device 2081; scratch quota NORMAL, 936,331,341 bytes used (<20 GiB).
- Batch reported selected 1,000: 868 PARSED, 113 SENSITIVE, 9 UNSUPPORTED_TYPE, 10 BINARY; zero errors and zero mirror recoveries.
- Direct SQLite/filesystem reconciliation: parser rows 71,968→72,968; statuses now 59,082 PARSED, 8,668 SENSITIVE, 3,333 UNSUPPORTED_TYPE, 1,690 BINARY, 174 TOO_LARGE, 21 UNSUPPORTED_ENCODING; provenance-aware pending 158,817→157,817; Markdown 58,214→59,082; outbox 0; global integrity `ok`, FK issues 0.
- Independently sampled ten latest PARSED rows: Markdown hashes/provenance and global-to-item mirrors all match, zero issues. SSD usage recheck: 936,331,341 bytes, free 31,442,272,256 bytes.
- Latest delta reconciles exactly. This does not prove root cause of older timing discrepancies and is not a full Markdown/parser audit or corpus-completion claim.

### Exact next action

Run the bounded parser command from `.progress/CONTINUATION_PROMPT.md`; immediately compare SQL status/pending deltas, Markdown count, outbox, integrity/FKs, latest sample mirrors/hashes, and SSD cap. Keep the original extraction sidecar discrepancies untouched.


## 2026-10-06 09:04 UTC — SSD-verified parser continuation

- New-source extraction is now at terminal input disposition: 68/68 sources have jobs; 58 VERIFIED, 10 FAILED closed; no pending/active jobs. The 10 refusals remain durable; raw source was untouched.
- Started CORPUS-0006 parsing after extraction stabilized. `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120` initialized and proved scratch on SSD device 2050 vs project device 2081. It selected and persisted 1,000 rows: 747 PARSED, 92 SENSITIVE, 114 UNSUPPORTED_TYPE, 41 BINARY, 6 TOO_LARGE; no errors/outbox.
- Direct SQLite reconciliation: parser rows 67,968→68,968; extracted outputs 230,785; simple outputs-without-current-version-row 161,817; Markdown 55,223→55,970; parse outbox 0; global DB integrity `ok` and FK 0. `--verify --limit 5 --offset 55220` checked 5 PARSED outputs, zero issues. This is sampled validation, not a full audit.
- SSD owned usage remains 936,331,341 bytes; free ~31.44 GB, normal quota status, under 20 GiB.
- Full suite after all changes: 57/57 passed; all Python scripts/tests compile. Existing non-failing SQLite ResourceWarnings noted.

### Exact next action

Continue bounded parser command from `.progress/CONTINUATION_PROMPT.md`, then reconcile all parser states/status counts, current pending set, Markdown hashes and global/per-item mirrors. Once parser tranche stabilized, run a current original-source extraction candidate reconciliation; the historic 297-item report is not current whole-corpus evidence.

## 2026-10-06 08:59 UTC — resumed remaining new-source extraction and reconciled terminal states

- Ran the state-aware batch after lease/scheduling fix. REPO-0410 and REPO-0411 resumed from safe journals to VERIFIED; REPO-0419 refused non-canonical path, FAILED closed. REPO-0417 rechecked and remains a symlink refusal.
- Independently checked REPO-0410/0411: source archive hash against inventory, every member hash/size, extraction metadata, and global/per-repository database member sets and rows; 8,324 files checked, zero discrepancies.
- Current new-source queue: 68/68 raw/manifest/job rows, 58 VERIFIED, 10 FAILED closed, zero PENDING/IN_PROGRESS; no active worker. Failures are seven symlink refusals, one duplicate/case-collision, one compression-ratio limit, one non-canonical path. Nothing executed.
- Global DB: 365 jobs (265 VERIFIED/37 BLOCKED/63 FAILED), 230,785 EXTRACTED outputs; SQLite integrity `ok`, FK check 0. Parser: 67,968 rows; outbox 0; 162,817 outputs have no row in the simple current-parser-version query. Full provenance-aware audit and Markdown reconciliation due.
- SSD: owned working files 936,331,341 bytes (<20 GiB), free bytes 31,443,644,416 at 08:59 UTC; quota severity NORMAL.
- Full test suite 57/57, focused batch/extractor 37/37, compilation checks pass. ResourceWarnings remain non-failing.

### Exact next action

Refresh the current whole-corpus candidate queue by reading the manifest/global SQLite and use `scripts/corpus_reconcile.py` in bounded mode on unprocessed original archive candidates. Then resume `scripts/corpus_parse.py` in bounded SSD-verified batches, checking DB output/parser counts, parse outbox, Markdown IDs/hashes and per-item mirrors. Keep raw sources untouched and do not mark any unresolved refusal complete.

## 2026-10-06 08:53 UTC — queue recovery, bounded extraction, and scheduler fix

- Re-read the live continuation state and checked host conditions. The active project root is not a Git repository; GitHub CLI is authenticated. Host: Ubuntu x86_64, 6 CPU cores (AMD FX-6100), about 19.3 GB RAM, AMD Radeon HD 7750 detected (compute support not verified). Raw corpus root has 349 direct files + `new/` (68 files); five historical project folders present under `old-dev/`.
- Reconfirmed the actual temp-path issue in a fresh shell: `tempfile.gettempdir()` is `/tmp` and TMPDIR/TEMP/TMP/SQLITE_TMPDIR/XDG cache/state are unset. SSD `/home/chris/data-processing` is `/dev/sda2` device 2050, `ROTA=0`; durable project is `/dev/sdc1` device 2081, reported `ROTA=1`. Existing workload CLIs configure process-local SSD use and prove a write; no global/system temp configuration was applied.
- Current `/home/chris/data-processing` owned regular-file usage is 936,331,341 bytes against 21,474,836,480 cap; free space during final check 31,444,176,896 bytes. The `processing_workspace.check_capacity()` diagnostic returned NORMAL.
- Ran the bounded new-source batch (12 max repos/240 sec/35 sec per archive). It moved additive verified count from 40 to 53, but surfaced an accounting bug: `extraction_state()` omitted lease columns, while status classification expected them. At first its run exhausted time retrying one large archive; no sources were skipped from the manifest.
- Corrected lease owner/expiry selection; added tests that distinguish an active lease from a safe PAUSED row. Added queue ordering that prefers never-attempted sources over paused resumes, preventing archive starvation. Focused new-source/extractor tests passed 37/37; full suite after final changes passed 57/57; `python3 -m py_compile scripts/*.py tests/*.py` passed.
- Re-ran bounded ingestion after scheduling change: REPO-0412, REPO-0413 and REPO-0418 reached VERIFIED. Independent read-only verification hashed their source archives and all 495 extracted members, then matched metadata/member sets with both global and per-repository extraction_outputs (193+126+176 files): 0 issues. A follow-on bounded check of REPO-0417 confirmed its unsafe-symlink refusal remains fail-closed. No corpus payload executed.
- Live direct DB reconciliation at 08:53 UTC: all 68 `repo/new/` sources match manifest and have jobs; 56 VERIFIED, 9 FAILED, 3 safe resumable IN_PROGRESS rows with no lease (REPO-0410/0411/0419), zero active workers. Global DB: 365 jobs (263 VERIFIED/37 BLOCKED/62 FAILED/3 safe pauses), 222,461 extracted output rows; integrity `ok`, foreign-key check 0. Parser has 67,968 rows and outbox 0; SQL finds 154,493 extracted outputs with missing/invalid current parser status.
- Final task/test warning: full suite emits existing non-failing sqlite ResourceWarnings from corpus inventory/test handling; left unrelated code unchanged.

### Exact next action

Run the bounded batch command in `.progress/CONTINUATION_PROMPT.md`; state-aware selection should process remaining never-attempted inputs before paused large archives. Reconcile live SQL/progress after the batch, inspect newly VERIFIED extraction outputs and per-item mirrors, and checkpoint. Then continue parser batches and full filesystem/Markdown reconciliation. Preserve all fail-closed refusals; keep SSD under 20 GiB. No whole corpus/product completion claim.

## 2026-10-06 07:41 UTC — SSD setup, parser state refresh, and additive corpus batches

- Diagnosed `/tmp` tmpfs use caused by unset TMPDIR/TEMP/TMP/SQLITE_TMPDIR. Confirmed `/home/chris/data-processing` is SSD `/dev/sda2`, dev2050, `ROTA=0`; durable project is `/dev/sdc1`, dev2081, `ROTA=1`. Verified actual fsync/read-back temp write on SSD.
- Added `scripts/processing_workspace.py`, process-local temp routing, SSD device probe, free/usage measurement, 20 GiB cap, 19/19.5 GiB warning/emergency thresholds, path safety; integrated into parser and additive extractor CLIs.
- Removed fixed 68-source expectation; stage now requires exact source/manifest name-set equality, validates safe unique paths/IDs and one per-repo file metadata row, verifies digest/size, fails closed on symlink or mismatch. Three-source fixture and refusal cases pass.
- Parser CLI bounded run processed 5 PARSED, reconciled +5 DB/Markdown and -5 pending, outbox remained zero; `--verify --limit 5` found no issues.
- Additive extraction advanced from 15 to 40 VERIFIED. REPO-0379 docjev resumed to VERIFIED after short safe pauses: source hash matches, 687 outputs / 79,968,863 bytes, independently hashed all output members with zero failures; global and per-item DB output sets match. REPO-0359 Kiln similarly resumed to VERIFIED. Other bounded priority batches processed REPO-0381/0385/0386/0388/0389/0390/0391/0392/0394/0395/0397/0400/0404/0406/0407/0409/0414/0415 and REPO-0353/0354/0356 to VERIFIED (40 additive verified total).
- Five unsafe/corrupt repositories remain FAILED closed: REPO-0374 symlink, REPO-0387 duplicate/case-colliding archive path, REPO-0393 symlink, REPO-0396 symlink, REPO-0416 symlink. No links followed or payload code executed. REPO-0359 pauses recovered and lease expired/released.
- Current additive queue: 68 manifest/raw inputs match; 40 VERIFIED, 5 FAILED, 23 PENDING, no active lease. `.progress/NEW_REPO_EXTRACTION_PROGRESS.json` refreshed with exact status counts, device, SSD usage, failed reasons and next command.
- Current global DB: 419 repositories, 313 extraction jobs (222 VERIFIED/37 BLOCKED/54 FAILED), 198,985 extraction outputs. Parser: 67,968 rows (55,223 PARSED, 8,056 SENSITIVE, 2,964 UNSUPPORTED_TYPE, 1,543 BINARY, 161 TOO_LARGE, 21 UNSUPPORTED_ENCODING), 131,017 pending, outbox 0, Markdown 55,223. This is direct DB state; the historical full parser audit is still due.
- SSD staged source use 936,331,341 bytes of 20 GiB; current write probe succeeds. All 422 managed DBs pass read-only integrity/FK checks.
- `python3 -m unittest discover -s tests -q`: 54/54 pass; py_compile passes. Non-failing ResourceWarnings remain in existing inventory/tests.
- Refreshed MASTER_PROGRESS, CURRENT_TASK, CONTINUATION_PROMPT, TASK_STATUS/QUEUE, known limitations, SSD architecture/progress, and additive JSON checkpoint. Product and corpus completeness are not claimed.

### Exact next action

Run `python3 scripts/corpus_new_batch.py --project . --corpus repo --scratch /home/chris/data-processing --batch-size 12 --wall-seconds 240 --per-call-seconds 35`, then independently reconcile each status/output against global/per-item DBs and hashes, inspect any PAUSED leases, and verify scratch remains under 20 GiB. 23 new repositories remain pending. Subsequently continue parser in bounded batches with immediate DB/Markdown/outbox reconciliation.

## Previous verified work — SSD routing and first recovery test

- Initial diagnosis: Python selected `/tmp` tmpfs because TMPDIR/TEMP/TMP/SQLITE_TMPDIR were absent. Confirmed SSD and rotational project devices differed.
- Implemented shared scratch setup, parser CLI probe, fail-closed new source staging and tests. First tiny recovery run safely paused REPO-0379 after three short passes; subsequent 120-second run resumed and verified it.
- Full suite then passed 53/53; see the section above for refreshed 54-test state.

## Historical logs

Earlier checkpoint narratives below are retained for provenance and may have stale counts/next actions. The latest top checkpoint and direct DB/filesystem state take precedence.
