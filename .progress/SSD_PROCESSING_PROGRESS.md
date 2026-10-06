# SSD Processing Progress

**Latest host check:** 2026-10-06 08:59 UTC — `/home/chris/data-processing` usage 936,331,341 bytes, free 31,443,644,416 bytes, normal quota status; hard cap 21,474,836,480 bytes. Filesystem device 2050 (`/dev/sda2`) differs from durable project device 2081 (`/dev/sdc1`). A fresh-shell Python process still defaults to `/tmp` tmpfs when temp environment variables are unset; the parser and batch extractor configure and verify scratch process-locally.

**Updated:** 2026-10-06 07:10 UTC

## Measured diagnosis

- Python originally returned `/tmp` from `tempfile.gettempdir()` because `TMPDIR`, `TEMP`, and `TMP` were unset. `/tmp` is tmpfs: the default was not the fast SSD.
- `/home/chris/data-processing` resolves to ext4 on `/dev/sda2`, device 2050, model TS128GSSD370S, `ROTA=0`. The durable project is on `/dev/sdc1`, device 2081, ext4, WDC Hitachi rotational disk (`ROTA=1` reported by `lsblk`). Separate devices verified.
- SSD had 31,458,082,816 bytes free at inspection. Project filesystem had 812,254,703,616 free. These are time-sensitive measurements.
- The SSD was already receiving staged new-ZIP data at `/home/chris/data-processing/private-ai-new-sources/`: 936,331,341 logical bytes. This is well below the 20 GiB hard cap. A `TMPDIR`-routed probe was created, fsynced, read back, verified by `st_dev=2050`, and removed.

## Implemented and verified

- `scripts/processing_workspace.py` creates private SSD subdirectories, routes process-local `TMPDIR`, `TEMP`, `TMP`, `SQLITE_TMPDIR` and Python `tempfile` to `/home/chris/data-processing/private-ai-tmp/tmp`, proves the actual temp write on the target device, measures existing usage, enforces projected use under 20 GiB, checks filesystem free space, flags 19/19.5 GiB warning/emergency thresholds, and rejects symlinks/special files.
- `scripts/corpus_new_batch.py` initializes this area before batch staging, records the measured devices/usage/probe in its durable progress JSON, reconciles every top-level raw `new/` file against the inventory manifest (no hard-coded expected repository count), and verifies hash/size for staged copies.
- `scripts/corpus_parse.py` now initializes and reports verified SSD routing on every CLI invocation; by default it refuses a scratch path sharing a filesystem device with the durable project. `--allow-same-device` is only for explicit test/degraded runs.
- The batch worker was exercised with a bounded two-repository selection/15-second wall limit. Result: REPO-0379 `docjev-main.zip` safely PAUSED after three short attempts (durable status `IN_PROGRESS` with lease released by worker); the next repo was explicitly deferred as PENDING. This did not execute corpus payloads and did not exceed the scratch quota. The batch's 68 input sources matched manifest paths.
- A parser CLI probe processed five text items, emitted its verified SSD startup diagnostic, and reconciled to five new `PARSED` records. A subsequent `--verify --limit 5` checked five records with zero issues.
- All 422 managed SQLite databases (421 per-repository files plus global DB) passed read-only integrity and foreign-key checks.
- Tests: full `python3 -m unittest discover -s tests -q` passed 53/53. Python compilation and the focused corpus/scratch suite passed. ResourceWarnings about pre-existing/unclosed DB handles in existing test code were emitted; they did not fail the suite.

## Next action / limits

Resume the new-source extractor in a bounded batch with a wall budget large enough for the current priority repository, checking the output JSON and global DB status after each batch. Reconcile on-disk occupancy against the 20 GiB cap during each batch. Continue parser processing in verified, bounded tranches, then directly reconcile counts/Markdown/mirrors. No prior batch's SSD use is claimed unless independently measured. This is not an operating-system-wide temp configuration and does not prove that every previous process used the SSD.
