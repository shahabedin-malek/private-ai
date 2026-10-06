# Current Task

**Active task:** CORPUS-0006 — continue bounded parser tranches on verified SSD scratch, then finish current-scope extraction and output reconciliation. Additive input disposition was last reconciled at 58 VERIFIED / 10 fail-closed FAILED.

**Latest verified checkpoint (2026-10-06 current session):** Corpus reconciled. Direct SQL shows **85,968** `stdlib-text-v3` rows (**69,911 PARSED**, **10,040 SENSITIVE**, **3,596 UNSUPPORTED_TYPE**, **2,220 BINARY**, **179 TOO_LARGE**, **22 UNSUPPORTED_ENCODING**); provenance-aware pending **144,817**; Markdown **69,911**; outbox 0. The newest tranche selected 1,000 with zero errors (850 PARSED, 98 SENSITIVE, 42 BINARY, 9 UNSUPPORTED_TYPE, 1 TOO_LARGE) in **60.438 s** (~993 rows/min). The newest 1,000 rows (offset 84,968) passed extraction provenance/per-item mirror and PARSED Markdown hash/provenance checks. Full paged audit previously covered 82,968 persisted rows with zero issues; the newest rows require inclusion next time. Python tests 57/57; py_compile passed. Global DB integrity `ok`, FK 0. SSD device 2050 vs project device 2081; usage 936,331,341 bytes (<20 GiB). Note: the prior documented total 83,968 contradicted its own stated breakdown, which summed to 84,968 (matching the DB pre-tranche). No active worker observed.

**Next exact action:** `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120`; after each tranche reconcile SQL deltas, pending query, Markdown, per-item mirrors, outbox, DB integrity/FKs and SSD quota. Then continue toward 144,817 remaining outputs; re-audit at a later batch boundary.

**Overall completion is not claimed.** Parser outputs pending: 144,817. Current-source extraction reconciliation reports four extra SQLite WAL/SHM sidecars in REPO-0154/0329; do not modify them without provenance. Additive extractions: 58 verified, 10 fail-closed. Research/product runtime remain incomplete.

---

**Historical checkpoint retained below (stale counts; use only as audit provenance):**

**Active task at earlier checkpoint:** CORPUS-0006 — continue bounded parser tranches on verified SSD scratch; investigate four current extraction reconciliation issues without deleting artifacts. Additive input disposition is terminal at 58 VERIFIED / 10 FAILED.

**Live new-repository state (direct DB and progress reconciliation, 2026-10-06 09:54 UTC):** `repo/new/` has 68 regular files matching 68 manifest paths; all 68 extraction jobs are terminal: 58 VERIFIED and 10 FAILED closed. No pending jobs, active leases, or extraction processes. Independent output audits: REPO-0410/0411, 8,324 member files, zero hash/size/global/per-item DB discrepancies; earlier REPO-0412/0413/0418 audit covered 495 more members. Do not bypass archive safety or execute corpus payloads.

**Scheduler correction:** extraction state now reads lease owner/expiry, and new repositories are prioritized before retrying paused large inputs. Tests cover active vs paused state and scheduling so the queue cannot starve unattempted inputs.

**Next exact command:**

```bash
python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120
```

After each parser batch, compare parser-version row counts/statuses and missing-output count directly in SQLite; validate Markdown output count/hash/provenance, the global-to-item mirror queue and item DB rows; verify SSD usage (<20 GiB). Continue bounded batches and retain explicit statuses for sensitive/binary/unsupported/unreadable items.

**Verified extraction example:** REPO-0410 (5,072 files) and REPO-0411 (3,252 files) have independently matched raw source SHA, every member hash/size, global rows, and per-repository rows; zero issues. REPO-0412/0413/0418 were independently verified across 495 files; REPO-0379 across 687 files. Current additive count is 58 VERIFIED.

**Global state (directly reconciled 2026-10-06 09:54 UTC):** 365 extraction jobs (265 VERIFIED, 37 BLOCKED, 63 FAILED, 0 IN_PROGRESS); 230,785 extracted output rows. Parser v3 has 72,968 rows (59,082 PARSED, 8,668 SENSITIVE, 3,333 UNSUPPORTED_TYPE, 1,690 BINARY, 174 TOO_LARGE, 21 UNSUPPORTED_ENCODING), 0 outbox, and 157,817 provenance-aware pending outputs. Markdown has 59,082 files; global DB integrity `ok`, foreign-key check 0.

**Failures:** REPO-0366/0374/0393/0396/0403/0416/0417 unsafe ZIP symlink members; REPO-0387 duplicate/case-colliding member path; REPO-0384 compression ratio exceeded policy; REPO-0419 non-canonical path. All remain fail-closed.

**SSD:** 936,331,341 bytes under `/home/chris/data-processing` (<20 GiB); temp write verified on device 2050, durable project on device 2081. Python launched outside initialized workload defaults to `/tmp` tmpfs; setup is process-local, not system-wide.

**Parser task after additive extraction batch:**

- Parser: `scripts/corpus_parse.py`, `stdlib-text-v3`, `corpus-parse-v4`, serialized lock and global `parse_sync_queue`.
- Current direct parser state: 230,785 extracted outputs; 71,968 parser rows (58,214 PARSED, 8,555 SENSITIVE, 3,324 UNSUPPORTED_TYPE, 1,680 BINARY, 174 TOO_LARGE, 21 UNSUPPORTED_ENCODING); simple missing-row SQL query returns 158,817; a full provenance/status-aware query and Markdown audit remain pending; outbox 0.
- `corpus_parse.py` initializes and checks SSD temp routing itself; verified device 2050 `/dev/sda2` versus project device 2081 `/dev/sdc1`; cap 20 GiB, current project scratch 936,331,341 bytes. Do not use `--allow-same-device` except tests/degraded fixtures.
- After extraction, run a bounded parser command, e.g. `python3 scripts/corpus_parse.py --project . --limit 1000 --max-mb 2 --max-wall-seconds 120`, then directly compare parser DB status deltas, pending outputs, outbox, Markdown ID set and per-item mirrors. Run full paged audit before declaring parser coverage.

**Validation:** full suite 57/57 passed; focused extraction/new-batch tests 37/37; `python3 -m py_compile scripts/*.py tests/*.py` passed. Global DB integrity `ok`, FK check 0. Existing non-failing SQLite ResourceWarnings remain. No full corpus completion is claimed.

**Known incomplete:** new-source queue is terminal at 58 VERIFIED / 10 FAILED (all refusals fail-closed). Current original candidate report covers 365/365 but reports four mismatches: extra SQLite WAL/SHM sidecars appeared under REPO-0154 and REPO-0329 output trees after extraction; do not remove them. Parser coverage and full Markdown/provenance audit remain incomplete; specialized formats/OCR/AST are unsupported. Historical import and all Private AI product-runtime subsystems remain pending.

**Immediate next action:** continue one bounded parser tranche with the exact command above; immediately reconcile SQL status deltas, pending outputs, Markdown count, outbox, global DB integrity/FKs, sampled per-item mirrors/Markdown hashes, and SSD cap. The latest invocation selected exactly 1,000 (868 PARSED, 113 SENSITIVE, 9 UNSUPPORTED_TYPE, 10 BINARY), with zero errors; direct SQL confirms parser rows increased 71,968→72,968 and pending fell 158,817→157,817, Markdown count rose 58,214→59,082, outbox stayed 0. Ten latest PARSED outputs passed Markdown hash/provenance and per-item mirror checks. This confirms this batch's persistence; it does not establish the cause of earlier timing discrepancies. Do not disturb the four original extraction report issues or raw sources.

---

**Historical CORPUS-0005 milestone:** `.progress/CORPUS-0005_RECONCILIATION.json` reports zero issues for 297 then-known original candidates. It predates new-source integration and must not be used as a current whole-corpus result. REPO-0159 was historically marked source-missing and must retain its stable ID.

<!-- Prior task/checkpoint narratives retained below; they are not live counts. -->
