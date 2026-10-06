# Database Progress

Global database: `data/database/private_ai_corpus.sqlite` — verified. 351 repository rows and 434 repository file rows remain; manifest includes missing-source REPO-0159 pending reconciliation. Extraction queue has 297 archive candidates: 115 VERIFIED, 26 BLOCKED, 53 FAILED, 1 resumable IN_PROGRESS (REPO-0239), 102 unclaimed. Global `extraction_outputs` currently contains 89,578 rows at checkpoint.

Per-item database files: 352 across 351 workspaces; REPO-0084 has a second empty legacy SQLite artifact. Global plus all 352 per-item SQLite files pass `PRAGMA integrity_check` and `PRAGMA foreign_key_check`. All 79 FAILED/BLOCKED terminal jobs have synchronized per-item job, file status, extraction and error records. Seven recent success outputs (REPO-0229/-0230/-0231/-0233–0236) independently match metadata and global/per-item output rows. Entity tables not populated by extraction remain placeholders; no scraping/Markdown knowledge records yet.
