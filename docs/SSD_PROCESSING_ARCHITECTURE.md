# SSD Processing Architecture

## Measured host state (2026-10-06)

- Processing SSD: `/home/chris/data-processing` is on `/dev/sda2`, ext4, device ID `2050`, model `TS128GSSD370S`, `ROTA=0`, mounted at `/`.
- Durable project/corpus: `/mnt/private-ai-data/privateai` is on `/dev/sdc1`, ext4, device ID `2081`, model `Hitachi HDS721010CLA332`, `ROTA=1`, mounted at `/mnt/private-ai-data`.
- The paths are different devices. At measurement, SSD filesystem free space was 31,458,082,816 bytes; project filesystem free space was 812,254,703,616 bytes. These numbers are a point-in-time measurement, not a reservation.
- `TMPDIR`, `TEMP`, `TMP`, `SQLITE_TMPDIR`, `XDG_CACHE_HOME`, and `XDG_STATE_HOME` were unset. Python reported `tempfile.gettempdir() == /tmp`; `/tmp` is a tmpfs, so relying on default temporary-file selection did not target the SSD.
- The corpus project root is intentionally durable on the data disk. Some atomic Markdown writes and resumable extraction staging are adjacent to canonical project outputs by design; setting `TMPDIR` alone cannot relocate explicit same-directory atomic writes.
- Existing new-repository ZIP staging is explicitly under `/home/chris/data-processing/private-ai-new-sources/`; its measured usage was 936,331,341 bytes. A bounded write probe using `TMPDIR=/home/chris/data-processing` created, fsynced, stat-verified on device `2050`, read back and removed a temporary file. The probe did not modify raw corpus data.
- A subsequent bounded parser CLI tranche (5 files) verified the shared initializer again and reported device `2050` vs project device `2081`; the temporary path was `/home/chris/data-processing/private-ai-tmp/tmp`. The five rows reconciled to SQLite and Markdown and passed per-item verification.
- The new-repository worker was first invoked with `--batch-size 2 --wall-seconds 15 --per-call-seconds 5`: REPO-0379 paused safely after three short calls. Later bounded 120–240 second passes resumed and VERIFIED REPO-0379 (687 files / 79,968,863 bytes) and REPO-0359. Current additive queue has 40 VERIFIED, 5 fail-closed failures, 23 pending and no active leases. This is not a corpus-completion claim or controlled throughput benchmark.

## Configuration and verification

`scripts/processing_workspace.py` is the common initializer used by the bounded new-repository batch worker. It creates private subdirectories (`tmp`, `work`, `cache`, `extract`, `scratch`, `staging`, `logs`, `index`), sets process-local `TMPDIR`, `TEMP`, `TMP`, and `SQLITE_TMPDIR` to the SSD `tmp` directory, resets Python's cached tempfile location, and verifies the actual write device and bytes with a temporary probe. Both the bounded new-ZIP staging worker and parser CLI initialize and verify this workspace; the parser CLI refuses a scratch root on the same device as the durable project root unless the explicit `--allow-same-device` test/degraded-mode flag is used. It rejects symlinks/special files and refuses to treat the durable project root as scratch.

For one-off parser work, configure the process explicitly before Python starts:

```bash
TMPDIR=/home/chris/data-processing/private-ai-tmp/tmp \
TEMP=/home/chris/data-processing/private-ai-tmp/tmp \
TMP=/home/chris/data-processing/private-ai-tmp/tmp \
SQLITE_TMPDIR=/home/chris/data-processing/private-ai-tmp/tmp \
python3 scripts/corpus_parse.py --project . --limit 10000 --max-mb 2 --max-wall-seconds 480
```

The batch worker itself initializes and verifies its scratch paths; it does not depend on an inherited shell environment. Canonical Markdown, manifests and authoritative SQLite databases remain under the project root. Temporary source copies and other reproducible scratch remain on the SSD and must be rebuildable from the raw sources/manifests.

## Working-space quota

The absolute limit is 20 GiB (`21,474,836,480` bytes); the normal operating target is at most 18 GiB, warning threshold 19 GiB, emergency threshold 19.5 GiB. `check_capacity` measures regular-file bytes beneath the configured processing root before work, enforces the absolute cap, checks filesystem free space, and labels NORMAL/WARNING/EMERGENCY thresholds. `scratch_usage` additionally rejects symlinks and non-regular objects; the ZIP staging worker checks projected bytes before each copy and verifies source digest/size before publishing each staged copy. No quota cleanup deletes data automatically; cleanup must be restricted to verified reproducible temporary artifacts, never raw sources, durable knowledge, or the only processing checkpoint.

## Current limitation

This is process-local setup and a verified bounded-batch integration, not a system-wide service configuration. It does not change mount options, move `/tmp`, install packages, alter systemd, relocate canonical outputs, or prove every historical parser/extractor run used the SSD. The previous parser run's unset environment meant its default temporary files went to tmpfs, while canonical outputs remained on the durable data disk. Continue adding scratch initialization to each workload explicitly and report the measured root/device/usage on each worker checkpoint.
