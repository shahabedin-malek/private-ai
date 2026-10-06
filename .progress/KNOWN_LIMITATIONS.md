# Known Limitations

**Updated:** 2026-10-06 07:41 UTC from direct SQLite/filesystem inspection.

- Durable inventory identities exist, but latest full raw-source audit is historical. REPO-0159 was recorded missing; preserve its stable identity and re-reconcile without inventing bytes.
- Global extraction database has 313 jobs: 222 VERIFIED, 37 BLOCKED, 54 FAILED and 198,985 EXTRACTED output rows. Candidate corpus items remain without extraction jobs; the historical 297-candidate reconciliation is not current whole-corpus completion evidence.
- New sources: 68 manifest entries exactly match 68 `repo/new/` files. Extraction now has 40 VERIFIED, 5 FAILED closed, 23 without jobs and 0 active leases. REPO-0379 `docjev-main.zip` and REPO-0359 `Kiln-main.zip` safely resumed and VERIFIED.
- Five new archive failures must remain explicit: REPO-0374, REPO-0393, REPO-0396, REPO-0416 refused unsafe symlink members; REPO-0387 refused duplicate/case-colliding paths. Do not weaken safety or execute payloads.
- Global parser DB has 67,968 `stdlib-text-v3` records of 198,985 extracted outputs: 55,223 PARSED, 8,056 SENSITIVE, 2,964 UNSUPPORTED_TYPE, 1,543 BINARY, 161 TOO_LARGE, 21 UNSUPPORTED_ENCODING; 131,017 outputs lack current rows. Full current Markdown/hash/per-item mirror audit is due. PDF/Office/image OCR/audio/video/code AST semantics are not implemented.
- SSD is `/dev/sda2`, device 2050, model TS128GSSD370S, ROTA=0; project data is rotational ext4 `/dev/sdc1`, device 2081. Initially TMPDIR was unset and Python used `/tmp` tmpfs. Parser/new-batch CLI routing/probes now exist but are process-local, not system-wide, and cannot retroactively prove historical IO placement.
- Current owned SSD staging usage is 936,331,341 bytes; last observed SSD free ~31.45 GB. Enforce the 20 GiB workspace cap. No automatic scratch cleanup is implemented.
- Latest read-only integrity/FK scan of all 422 managed DB files passed; a separate embedded corpus-fixture DB FK anomaly was documented earlier and remains unchanged.
- No semantic model/runtime/provider registry, memory, agent system, tools/MCP/A2A, research worker, production CLI/API/Web/VS Code, media/voice, service supervision or deployment has been implemented/verified in active project.
- Historical review is evidence-bounded; the 6.1 GiB backup remains unopened; historical runtime tree was dirty; legacy knowledge import remains pending.
- Several old detailed progress entries remain stale; prefer live SQLite/filesystem and current top controller counts.
