# Extraction Progress

**Updated:** 2026-10-06 07:41 UTC from global SQLite, per-repository DBs, and SSD staging.

## Live status

- Additive `repo/new/` files: 68 regular top-level sources; 68 manifest records; exact path/name set match.
- Additive extraction DB: **40 VERIFIED**, **5 FAILED**, **23 PENDING with no job**, **0 active leases**. Expired IN_PROGRESS jobs are represented as PAUSED in the progress JSON view.
- Overall global extraction DB: **313 jobs** — 222 VERIFIED, 37 BLOCKED, 54 FAILED; 198,985 extracted outputs. Many source archive/package candidates remain without extraction jobs. The historical 297-candidate CORPUS-0005 audit predates additive items and is not complete current corpus verification.
- Safe additive output verification example: REPO-0379 `docjev-main.zip`, source SHA matches inventory/job; 687 extracted members, 79,968,863 bytes, all members rehashed with zero mismatch; global/per-item member path sets agree and per-item/global DB integrity/FK pass. REPO-0359 `Kiln-main.zip` was safely resumed from PAUSED and verified.
- Five failed-closed cases: REPO-0374, REPO-0393, REPO-0396, REPO-0416 refused unsafe ZIP symlink members; REPO-0387 refused duplicate/case-colliding member path. No symlink followed, no corpus payload executed. Preserve explicit failures unless an evidence-backed safe extraction alternative is implemented.
- SSD: `/home/chris/data-processing` is device 2050 (`/dev/sda2`, SSD, ROTA=0); project root device 2081 (`/dev/sdc1`, ROTA=1). Verified process-local Python/SQLite temp probe on SSD. Staged immutable raw archive bytes are 936,331,341 bytes (<20 GiB hard cap).
- All 422 managed SQLite databases pass `integrity_check` and `foreign_key_check`.

## Exact continuation

```bash
python3 scripts/corpus_new_batch.py --project . --corpus repo --scratch /home/chris/data-processing --batch-size 12 --wall-seconds 240 --per-call-seconds 35
```

After every batch, reconcile `.progress/NEW_REPO_EXTRACTION_PROGRESS.json` against global and per-item SQLite state, hashes, output counts, leases and scratch usage. Continue until each additive repo is VERIFIED or has a durable FAILED/BLOCKED reason. Then parse output files in bounded SSD-routed batches. Extraction statuses are not a corpus-completeness claim.
