# Errors and Retry Register

## 2026-10-06 09:54 UTC — parser batch delta verified

- CORPUS-0006 selected 1,000 records, reported zero errors, and direct SQLite/filesystem reconciliation matched the exact delta (+1,000 current parser rows, -1,000 provenance-aware pending outputs, +868 Markdown records; outbox stayed 0). Latest ten PARSED records passed Markdown hash/provenance and per-item mirror checks. No new failure to register. This validates the current tranche only; the cause of historical delayed/stale reads remains unknown.


## 2026-10-06 09:30 UTC — current whole-candidate audit findings

| Task | Error | Tool/version | Retry | Resolution and verification | Next action |
|---|---|---|---:|---|---|
| CORPUS-0005 current reconciliation / REPO-0154 | Published tree contains 30 additional SQLite `-wal`/`-shm` sidecars under extracted test fixtures that were not in original ZIP member metadata; tree digest/member set no longer matches. Sidecars appeared after extraction (mtime later than metadata) and exact member names do not occur in the raw ZIP. SQLite reads of fixtures can create these runtime artifacts. | `corpus_reconcile.py` reconcile-v1; Python sqlite3 runtime | 0 destructive repair attempts | Corpus read-only extraction output left unchanged; all sidecars preserved for audit. Root cause strongly consistent with SQLite analysis adding sidecars, but not proven for every file. | Future analysis must use immutable original plus isolated/copied DBs or SQLite immutable URI and output stores must explicitly classify reproducible analysis artifacts; review provenance before repair. |
| CORPUS-0005 current reconciliation / REPO-0329 | Published tree contains 2 extra SQLite `-shm`/`-wal` sidecars under extracted test database not in ZIP member list; published digest/member set fails current reconciliation. | `corpus_reconcile.py` reconcile-v1; Python sqlite3 runtime | 0 destructive repair attempts | Left outputs untouched; sidecars are visible and attributable to runtime artifact class, not in source ZIP. | Same as above; preserve evidence, add explicit artifact provenance strategy before deciding whether/how to exclude.


| Task | Error | Tool/version | Retry | Resolution and verification | Next action |
|---|---|---|---:|---|---|
| CORPUS-0006-NEW-ZIPS scheduling | `extraction_state()` queried only status/attempt/error/next_action, omitting `lease_owner` and `lease_expires_at`; checkpoint classifier expected expiry and had labeled active leases as paused. Under priority ordering, paused high-priority archives also starved never-attempted inputs. | `scripts/corpus_new_batch.py`, Python 3.14.4 | 2 bounded batches | Added lease columns; regression tests validate active lease classification and new-input scheduling before paused retries. Re-ran successfully and verified 3 repositories / 495 output members against source, extraction metadata, global and per-item SQLite (zero issues). Full suite 57/57 and py_compile passed. | Continue state-prioritized bounded queue; inspect every checkpoint against direct SQL. |
| CORPUS-0006-NEW-ZIPS / REPO-0417 | Extraction refuses symlink member `tweakcc-main/CLAUDE.md`. | `corpus_extract.py`, safe-extract-v6 | 1 follow-up bounded check | FAILED closed; raw source left untouched; no symlink followed; no payload executed. | Keep refusal durable; do not bypass archive safety. |
| CORPUS-0006-NEW-ZIPS / REPO-0384 | Compression ratio 232.4 for a database SHM member exceeds configured ratio ceiling 200. | `corpus_extract.py`, safe-extract-v6 | 3 attempts terminal | FAILED closed under policy; preserve reason pending a safer, member-specific bounded method. | Do not raise global ratio cap blindly. |
| CORPUS-0006-NEW-ZIPS / REPO-0419 | ZIP member rejected as non-canonical or traversing path by safe extraction. | `corpus_extract.py`, safe-extract-v6 | 8 resumable attempts before terminal refusal | FAILED closed; no unsafe path published. | Keep reason and source immutable; review only a specifically validated safe handling strategy. |
| CORPUS-0006-NEW-ZIPS / REPO-0410, REPO-0411 | Initial work was paused at bounded call deadlines. | `corpus_new_batch.py`, safe-extract-v6 | 2 / 1 additional resumes | Both resumed from journaled staging, VERIFIED; independently audited 8,324 members and global/per-item rows with zero discrepancies. | Do not repeat extraction; parser queue may consume these outputs. |

## 2026-10-04 — live recovery register additions

| Task | Error | Tool/version | Retry | Resolution and verification | Next action |
|---|---|---|---:|---|---|
| CORPUS-0005 / REPO-0229 | Default `max_members=10,000` refused ZIP with 11,938 entries. | `corpus_extract.py`, safe-extract-v6 | 1 failed by policy, then 14 resumable passes | Explicitly raised cap to 20,000 and total expanded cap to 512 MiB; preserved validated staging, eventually VERIFIED 10,735 files/115,274,347 bytes; independent source/member/tree and DB verification all passed. | Continue to reuse verified output; do not re-extract. |
| CORPUS-0005 / REPO-0230 | One tar member `koder` exceeded default 32 MiB single-member limit. | `corpus_extract.py`, safe-extract-v6 | 1 failed by policy, 1 reviewed retry | Re-ran with per-member max 256 MiB and total cap 512 MiB; VERIFIED 2 files/156,721,685 bytes; independent output and DB verification passed. | No retry needed. |
| CORPUS-0005 / REPO-0237 | ZIP member count 60,162 exceeds selected max 20,000. | `corpus_extract.py`, safe-extract-v6 | 1 | Failed closed, no output claimed, durable global/per-item error record. | Review stronger per-item bounds or alternate vetted streaming reader; keep terminal FAILED until a legitimate bounded strategy is used. |
| CORPUS-0005 / source inventory | REPO-0159 `entire_linux_arm64.tar.gz` recorded active but absent from current raw source; raw root has 350 top-level entries vs 351 active inventory identities. | filesystem vs manifest/DB | 0 | Confirmed `exists=False`, no similar replacement source; stable IDs retained and no bytes fabricated. | Reconcile item to MISSING using inventory procedure without renumbering; then validate manifest/global/per-item implications. |
| CORPUS-0005 / REPO-0239 | Large ZIP exceeded 75-second internal wall budget during first bounded pass. | `corpus_extract.py`, safe-extract-v6 | 0 retries so far | PAUSED safely; lease released; 1,881 extracted staging files (24,502,126 bytes), last member `members/locally-uncensored-master/src/hooks/__tests__/der-agentenzug-endet-nicht-wortlos.test.ts`; later VERIFIED as 2,766 files / 31,816,730 bytes / tree SHA `6ee371579d2e7e42f62da579d384a56afb178f1adbe9b24704fcb0e981f5c477`. | Resume using CURRENT_TASK command, 75-second budget per pass. |

## Resolved / recovered

| Task | Error | Tool/version | Retry | Resolution and verification | Next action |
|---|---|---|---:|---|---|
| CORPUS-0002 | Initial full inventory exceeded 600 s after 185 per-item workspaces/DB skeletons; final manifest not yet published. | Python 3.14.4, CLI time limit | 1 | Added atomic per-item JSON checkpoints, lstat-based cache validation and bounded `--offset/--limit` batches. Completed all items in batches and independently verified paths/hashes/counts/DBs. | Use the continuation batch command for future inventories. |
| CORPUS-0001 | Fixture rerun found `file_hashes.file_id` uniqueness error. | Python `sqlite3` | 1 | Added `ON CONFLICT` update and upsert of files/repositories; focused tests pass. | None. |
| CORPUS-0001 | Inventory manifest initially had stale byte count as one source artifact changed size between scans. | filesystem metadata/hash revalidation | 1 | Checkpoint invalidated via lstat size/mtime identity; item rehashed; final manifest matches current 434 source files and 16,820,747,697 bytes; all hashes independently recomputed. | Treat future source changes as checkpoint invalidation; do not infer this tool modified raw input. |
| CORPUS-0001 | Initial full inventory timed out. | Python 3.14.4 + unittest | 1 | Corrected code; `py_compile` and 7/7 inventory fixture tests pass. | None. |
| CORPUS-0005 | Initial real pilot failed before publish because manifest omits `workspace_path`; global DB has it. | Python 3.14.4, extraction worker | 1 | Corrected fallback, REPO-0001 independently verified. | None for this row. |
| CORPUS-0005 | Earlier generic `--limit 10` call exceeded 300 s and persisted REPO-0013 as IN_PROGRESS in stale checkpoint notes. | Python stdlib, command timeout | 1 | Filesystem/global DB reinspection shows REPO-0013 is actually VERIFIED with published output; no live process. The notes were stale. | Do not reprocess REPO-0013. |
| CORPUS-0005 | Global FAILED/BLOCKED jobs did not all mirror terminal status into per-item DBs. | SQLite reconciliation | 1 | Reconciled all 31 terminal global job records; 17 stale/missing per-item mirrors repaired. All 351 per-item DBs and global DB pass integrity/FK checks. | Verify per-item mirror during future terminal reconciliation. |
| CORPUS-0005 | REPO-0083 ZIP exceeded tool window; first two resume attempts timed out before internal pause feature existed. | Python stdlib worker, 120 s command cap | 2 | Added safe-extract-v6 verified journal staging resume and `--max-wall-seconds`/`--lease-seconds`. A bounded call returns PAUSED, releases lease, preserves stage. Tests 33/33 pass. | Continue REPO-0083 from staging with 80 s internal budget until VERIFIED. |
| CORPUS-0005 | Initial recovery design re-read/decompressed all existing archive members on every short pass, so large ZIP still timed out without enough progress. | Python stdlib ZIP reader | 1 | Revised recovery: verify staged files against journal hashes/sizes and whole source against inventory hash; compare journaled members to source directory metadata, skipping prior output writes. Subsequent bounded calls advance. | Keep calls bounded; independently reconcile full extraction after publication. |
| CORPUS-0005 | A short first pass on REPO-0084 hit wall budget before any member was journaled. | Python stdlib worker | 0 | Job is safely PAUSED/IN_PROGRESS with released lease and empty staging; safe to retry. | Resume after REPO-0083. |

## Active work / recoverable queue — refreshed 2026-10-06

Current controller and live checkpoint replace stale parser-era counts below; CORPUS-0005 extraction reconciliation is verified and inactive.

The table in this section contains historical parser checkpoint notes in addition to the current row. Do not treat older rows/counts as live state; check `CONTINUATION_PROMPT.md` and query SQLite.

| CORPUS-0006 | Historical batch report/DB delta discrepancy | `corpus_parse.py` stdlib-text-v3 → schema migration `corpus-parse-v4` | Recurred in earlier multi-item calls; original initiating event not identified | Recovered live baseline 14,273 rows / 177,913 pending; implemented serialized invocation lock and durable global-to-item mirror outbox with verified acknowledgement; injected interruption test passes. One 10,000-selection request processed 1,351 before wall limit and reconciled exact SQL/filesystem. Current 15,624 records, 176,562 pending, 12,843 Markdown, 0 outbox, 0 parse errors. | Continue 10,000-selection/480-second bounded runs, immediate DB/outbox/Markdown reconciliation and periodic audit; do not claim historical cause proven. |

| CORPUS-0006 | Batch report vs DB delta | `corpus_parse.py` stdlib-text-v3 | Recurred at 1,152-row checkpoint | Earlier invocation at 500 rows and later invocation after 1,127 rows both reported selected output and lowered pending, but the immediate read-only DB count remained unchanged. At the latter checkpoint the pending sample contained REPO-0002 extracted ID `91a7c5a6d7ed943bb0983f706a46967e43365bdd6c551c826c23c9ef9572e01c`; a one-item rerun persisted it, and successive one-item calls each matched +1 DB row/-1 pending. Subsequent audit passed. Root cause remains unknown. | Continue in `--limit 1` mode and query DB after each call; do not trust batch summary until mismatch is explained. |


| Task | State | Last verified checkpoint | Exact next action |
|---|---|---|---|
| CORPUS-0006 parser v3/v4 | IN_PROGRESS; no active foreground batch after checkpoint | Live 40,635/192,186 rows: 32,447 PARSED, 5,626 SENSITIVE, 1,354 UNSUPPORTED_TYPE, 1,058 BINARY, 129 TOO_LARGE, 21 UNSUPPORTED_ENCODING; 151,551 pending; 32,447 Markdown; queue/errors 0. Full audit covered all 40,635 records with zero issues; v4 outbox recovery test and 39/39 focused tests pass. Grouped commits improved one 10,000-selection tranche from 1,351 to 8,964 before wall cap. | Run bounded 10,000 selection on SSD scratch (`TMPDIR`/`SQLITE_TMPDIR`); verify direct SQL pending/status, queue, Markdown ID equality after each; periodic `--audit --limit 500`. Full managed DB integrity/FK scan to refresh. |
| CORPUS-0005 extraction reconciliation | VERIFIED at recorded scope | 297 candidates reconciled; 207 VERIFIED, 37 BLOCKED, 53 FAILED, one manifest-MISSING source REPO-0159; zero reconciliation issues | Reuse verified outputs; do not rerun extraction. Escalate only on a verified integrity/source discrepancy. |
| CORPUS-0005 REPO-0237 | FAILED, terminal policy refusal | 60,162 ZIP entries exceeds 20,000 configured cap; durable reason retained | Review stronger per-item bounds or alternate vetted streaming reader only as a separate task; never claim success without complete accounting. |
| CORPUS-0005 REPO-0159 | Source item missing | Manifest retains stable ID; source archive absent and reconciliation classified it MISSING | Preserve provenance and stable ID; do not recreate or renumber. |

## Limitations (not task failures)

- Extraction utilities `bsdtar`, 7z, rpm, cabextract, Tika, exiftool, binwalk, ctags, Java and SQLite CLI are not detected.
- No installed local inference runtime/model. AMD GPU acceleration availability has not been established.
- Historical project audit is bounded; 6.1 GiB backup archive not opened.
- Historical runtime Git worktree is dirty and contains credential-risk source material; it is not the active root.
- Parser v3/v4 is a partial text-only rollout; 151,551 outputs remain without current parser rows at latest verified checkpoint. Non-text parser coverage, research queue, memory and product runtime/UI remain pending.

### Newly observed corpus-content database condition (2026-10-06)

A read-only recursive scan of 380 SQLite-like files under `data/` found one extracted fixture database at `data/repos/REPO-0154-emdash-main.zip/extracted/53433744e28c746a8d527c54/members/emdash-main/apps/emdash-desktop/tooling/fixtures/pre-0022.db` with `PRAGMA integrity_check=ok` and one `foreign_key_check` violation (`automation_runs` → `automations`). It is an embedded corpus artifact, not one of the 354 managed global/per-item state databases; it was not modified. The 354 managed DBs pass both checks. Assess embedded database fixtures as corpus content if their own semantic integrity becomes an explicit task.
