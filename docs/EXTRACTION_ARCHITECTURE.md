# Extraction Architecture

## Initial environment inventory

Available: Python 3.14.4/stdlib `zipfile`, `tarfile`, `gzip`, `bz2`, `lzma`, `sqlite3`; `tar`, `unzip`, `ar`, `dpkg-deb`, `cpio`, `file`, and `strings` executables. Not detected: `bsdtar`, `7z`, `rpm`, `cabextract`, `tika`, `exiftool`, `binwalk`, `ctags`, `sqlite3` CLI, Java, or tree-sitter. Pillow is installed; PDF, BeautifulSoup and tree-sitter Python modules were not detected. No model runtime is installed. Do not install tools without a measured need.

## Processing stages

1. Inventory/lstat/hash without following symlinks.
2. Detect signatures/MIME and classify confidence; extension is only a hint.
3. Queue archive members under a durable lease.
4. Enumerate entries before writing any payload; reject absolute paths, `..`, drive paths, device/special members, escaping links, duplicates that collide after normalization, and unsupported encryption.
5. Enforce configurable max depth, member count, single-member bytes, total expanded bytes, compression ratio, wall time and free-disk floor.
6. Write through a confined destination using atomic temp files; verify member/output digests and commit output metadata only after verification.
7. Recursively enqueue nested archives. Never invoke payload executables or install hooks.
8. Record every refusal/failure with repository ID, file, detected type, error, tool/version, timestamp, attempt count and next action.

## Recovery

A worker claims jobs using a SQLite lease. Per-member staging and a journal make retries idempotent. On restart, verify existing outputs against their recorded hashes and queue bounds before resuming; otherwise quarantine partial work and record the reason. An exception for one file never prevents processing independent jobs.

## Tool baseline measured on Ubuntu 26.04 (2026-10-04)

Installed and available: Python stdlib `zipfile`, `tarfile`, gzip/bz2/lzma; `tar`, `unzip`, `ar`, `dpkg-deb`, `cpio`, `file`, and `strings`. Not detected: `bsdtar`, `7z`, `rpm`, `cabextract`, Java or Apache Tika. Inventory found 297 archive candidates among the source file rows; candidates are signature/type inventory classifications only.

## Implemented extraction slice (CORPUS-0005)

`scripts/corpus_extract.py` currently supports ZIP, TAR, gzip, bzip2 and xz using Python stdlib readers. It enumerates and validates members before any writes; refuses traversal, non-canonical/portable-name collisions, symlinks, hardlinks, special files and encrypted ZIP members; verifies actual byte counts and SHA-256; and enforces configurable input/member/total/ratio/depth/path/time/free-space bounds. A file is atomically staged under a per-source output directory and never executed. Each extracted member and refusal/failure is recorded with provenance in the global DB, and successfully indexed extractions are mirrored to the matching repository DB.

The global job table supplies expiring leases, attempt limits, blocked/failed states and next actions. A durable append-only staging journal records member outcomes. Recovery verifies every journaled staged file's confined path, type, size and SHA-256 against its record; the source archive SHA-256 is checked against the inventory before reuse. Valid members are skipped and extraction resumes through the source listing; invalid/corrupt staging is recorded and discarded safely. A configurable internal wall-time budget pauses large work items before the command timeout, releases the lease, and preserves verified staging for the next worker pass. Published filesystem output includes its source hash, configured limits, pipeline/tool versions, member hashes, timestamps and a deterministic tree digest. A verified output is cross-checked against on-disk bytes and database member rows before reuse. If filesystem publication succeeds but database indexing fails, the next worker pass indexes verified output without re-extracting. Successful output/provenance and terminal failure/block status/errors are mirrored between global and per-repository DBs. Unsupported package/archive types become terminal `BLOCKED` records with explicit parser/tool next actions; bad archives become `FAILED` with retry limits.

Pipeline checkpoint `safe-extract-v6` adds valid-staging resume and internal time-budget pause; corruption fails closed to clean retry. Do not treat a `PAUSED` result as terminal verification.

## Real corpus checkpoint (2026-10-04 — current live state)

Inventory baseline retains stable IDs REPO-0001–0351 and 297 archive candidates. Current filesystem root has 350 top-level entries; active manifest includes REPO-0159 (`entire_linux_arm64.tar.gz`) but that source file is missing. This mismatch must be reconciled without renumbering. Current extraction DB counts: 115 VERIFIED, 26 BLOCKED, 53 FAILED, one resumable IN_PROGRESS (REPO-0239), 102 unclaimed. All 79 terminal failures/blocks mirror into per-item DBs. Global DB and 352 per-item SQLite files pass integrity/FK checks; REPO-0084 has an additional empty legacy SQLite artifact, also healthy.

The previously stale REPO-0083/-0084/-0094 references are complete in live DB. Most recent verified tranche: REPO-0229 (10,735 files/115,274,347 bytes/tree SHA `3bfd382e2ec6a880c69a6fbef019bd9b4d39bb2b79486e2df37f2bc7e2a984d1`), -0230 (2/156,721,685), -0231 (23/1,531,536), -0233 (277/2,934,325), -0234 (301/3,042,401), -0235 (103/790,731), -0236 (118/871,339), and -0238 (266/1,304,326). REPO-0229/-0230/-0231/-0233–0236 independently reconciled source/member/tree hashes and global/per-item records. REPO-0237 remains FAILED: 60,162 entries above the 20,000 member cap.

REPO-0239 (`locally-uncensored-master.zip`) is the current resume target. Journal currently has 935 EXTRACTED file records and 12,066,574 bytes, last `members/locally-uncensored-master/src-tauri/gen/schemas/desktop-schema.json`; status IN_PROGRESS, lease owner NULL/expiry 0. Resume with one-repository calls: `python3 scripts/corpus_extract.py --root repo --output . --repo-id REPO-0239 --limit 1 --lease-seconds 105 --max-wall-seconds 75 --max-members 20000 --max-member-mb 256 --max-total-mb 512 --max-attempts 20 --owner recovery-20261004-follow-on`. Do not interpret PAUSED as success.

Focused coverage: `python3 -m unittest tests.test_corpus_extract tests.test_corpus_inventory -v` (33 tests) and `python3 -m py_compile scripts/corpus_extract.py tests/test_corpus_extract.py scripts/corpus_inventory.py tests/test_corpus_inventory.py`. The 297-item extraction queue is incomplete; scraping is still 0 and no corpus-completion claim is made.
