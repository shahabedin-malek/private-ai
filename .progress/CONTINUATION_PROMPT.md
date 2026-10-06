# Live Continuation Controller

**PROJECT:** Private AI — `/mnt/private-ai-data/privateai/`
**PHASE:** PHASE 6 — bounded corpus parsing and current-scope source/extraction reconciliation.
**TASK:** CORPUS-0006; CORPUS-0005 current-scope reconciliation remains open.
**SUBTASK:** Process another bounded parser tranche, independently reconcile it, then continue toward a full parser/Markdown audit and source reconciliation.
**REPOSITORY:** Global parser queue across extracted files; no active worker observed after the latest batch.
**FILE:** Next 1,000 eligible extracted members selected from global SQLite.
**STAGE:** Parse → commit DB → mirror per-repository DB → verify hashes/provenance/Markdown → reconcile.

## Last verified output (2026-10-06 current session)

Bounded SSD-routed parser tranches of 1,000 completed with no reported errors. Newest measured tranche: 850 PARSED, 98 SENSITIVE, 42 BINARY, 9 UNSUPPORTED_TYPE, 1 TOO_LARGE; **60.438 s** wall time (~993 rows/min). Direct SQL now reconciles parser rows to **85,968**; provenance-aware pending **144,817**; Markdown **69,911**; outbox 0. The newest 1,000 rows (offset 84,968) passed extraction provenance and per-item mirror checks; PARSED Markdown passed hash/provenance checks. Full paged `--audit --limit 1000` passed 82,968 persisted parser rows before the newest tranches; newer rows need inclusion in the next full re-audit. Global DB `integrity_check=ok`, FK issues 0. Note: the prior documented total 83,968 contradicted its own status breakdown, which summed to 84,968 (DB confirmed 84,968 pre-tranche).

## Live inventory/task ledger

- **TOTAL / DISCOVERED:** 230,785 global EXTRACTED outputs; all represented as parser candidates in current queue.
- **PENDING:** 144,817 outputs lack a valid current `stdlib-text-v3` parser record.
- **IN_PROGRESS:** No parser/extractor process observed after synchronous batch; no active extraction job reported.
- **COMPLETED:** Overall corpus/parser completion not claimed.
- **VERIFIED:** 85,968 parser rows persisted; 82,968 were fully audited at the last full re-audit; not full-queue completion.
- **FAILED:** Latest parser tranche had zero errors; 63 global extraction jobs currently FAILED.
- **BLOCKED:** 37 global extraction jobs.
- **RETRYING:** No active retries/workers observed.
- **GLOBAL EXTRACTION:** 365 jobs total (265 VERIFIED, 37 BLOCKED, 63 FAILED); 230,785 extracted output rows.
- **ADDITIVE `repo/new/`:** Last reconciled 68/68 sources with terminal states: 58 VERIFIED, 10 fail-closed FAILED. This is input-disposition scope only.
- **PARSER COUNTS:** **85,968** total: **69,911 PARSED**; **10,040 SENSITIVE**; **3,596 UNSUPPORTED_TYPE**; **2,220 BINARY**; **179 TOO_LARGE**; **22 UNSUPPORTED_ENCODING**.
- **MARKDOWN:** **69,911** files, equals PARSED rows.
- **DATABASE:** parser outbox 0; global integrity `ok`; FK check 0.
- **CURRENT WORKER:** none observed; parser flock serializes calls.

## Next exact action

Run one bounded parser tranche, then query SQLite and independently verify the row/pending deltas, latest Markdown hashes/provenance, per-item mirrors, outbox/errors, DB integrity/FKs, and SSD cap. Continue bounded tranches. Existing-row audit passed for 82,968 rows; 144,817 extracted outputs remain pending. The latest 1,000-row tranche still awaits inclusion in the next paged full audit. Run another paged full audit later, and continue current-scope source reconciliation.

```bash
python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120
```

## SSD and temp routing

- `/home/chris/data-processing`: device 2050, ext4 `/dev/sda2`; durable project device 2081 (`/dev/sdc1`).
- Last measured owned usage: 936,331,341 bytes; cap 20 GiB; NORMAL. Free space ~31.09 GB at measurement (time-sensitive).
- Parser CLI actively probed temp write/readback on SSD path `/home/chris/data-processing/private-ai-tmp/tmp` and emitted `probe_verified=true`.
- Fresh shell has TMPDIR/TEMP/TMP/SQLITE_TMPDIR unset; Python default remains `/tmp`. SSD routing is explicit/process-local in workload CLIs, not global.

## Known errors and safety constraints

- Current extraction-candidate report has four mismatches: extra SQLite WAL/SHM sidecars in REPO-0154 and REPO-0329 output trees. Preserve these artifacts pending provenance; do not delete or mutate.
- Additive fail-closed extraction refusals: unsafe symlink members REPO-0366/0374/0393/0396/0403/0416/0417; duplicate/case collision REPO-0387; compression-ratio policy refusal REPO-0384; non-canonical path REPO-0419. Do not bypass safety or run corpus code.
- Progress documents contain older counts; use fresh DB/filesystem state rather than stale historical rows.

## Other project status

- **RESEARCH:** no research worker or verified JEV research yet.
- **DEVELOPMENT:** corpus inventory/extraction/text parser foundation; no finished Private AI runtime/product.
- **TESTS:** `python3 -m unittest discover -s tests -q` passed 57/57 this session; two non-failing SQLite ResourceWarnings. `python3 -m py_compile scripts/*.py tests/*.py` passed.
- **GIT:** no usable Git metadata in project root; no clean/commit claim.
- **DEPLOYMENT:** not implemented/verified.
- **TRIGGER.DEV:** config/typecheck/five pure guard tests previously verified; worker startup, registration, health run, retry/restart and MCP connection remain unverified.
- **MODELS/PROVIDERS:** no model runtime/provider integration verified; Ollama optional only.
- **TOOLCHAIN:** Ubuntu x86_64, Python 3.14.4, 6 CPU cores, ~19.3 GB RAM.
- **ARCHITECTURE:** v0.2 inventory/extraction/parser foundation; product incomplete.

**LAST CHECKPOINT:** 2026-10-06 current session; corpus reconciled to 85,968 parser rows / 144,817 pending; newest 1,000 rows audited clean; prior full audit passed at 82,968 rows; Python tests 57/57.
**NEXT CHECKPOINT:** After the next bounded tranche and its independent reconciliation.
