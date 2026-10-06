# Data Model

## Identity

- `repository_id`: stable `REPO-0001` style identifier assigned in deterministic first-discovery order and retained by original path (with device/inode fallback) on later inventory runs.
- `file_id`: repository ID plus digest of the relative path. Content changes update that file's hash; a rename is a distinct path-level identity and duplicate-content relationship.
- SHA-256 identifies bytes, not a project/repository's semantic identity.

## Current inventory database baseline

The inventory script creates `data/database/private_ai_corpus.sqlite` and one SQLite file under each `data/repos/<REPO-ID>-<slug>/db/`. Schema v1 creates repository/file/hash indexes, directories, archive candidates, extraction placeholders, metadata, pending text content, code symbols/imports/dependencies, URLs/entities/technologies/features/commands/packages/relationships, research source/claim placeholders, provenance, processing runs and processing errors. The global DB creates the requested logical entity families as typed extensible payload tables plus an FTS5 table when SQLite supports it (otherwise a plain-table fallback). Empty logical tables are schema placeholders, not ingested records. Schema evolution will be migration-controlled before long-lived ingestion behavior.

## Required global entities

`repositories`, `repository_files`, `file_hashes`, `directories`, `archives`, `extracted_files`, `file_metadata`, `text_content`, `code_entities`, `code_symbols`, `imports`, `dependencies`, `packages`, `executables`, `urls`, `domains`, `organizations`, `people`, `products`, `projects`, `technologies`, `frameworks`, `models`, `apis`, `services`, `commands`, `features`, `capabilities`, `categories`, `tags`, `knowledge_documents`, `research_sources`, `research_claims`, `relationships`, `duplicates`, `similar_files`, `memory_records`, `conversation_records`, `task_records`, `processing_runs`, `processing_errors`, `tool_registry`, `model_registry`, `provider_registry`, `token_usage`, `search_events`, `research_events`, and `audit_log`.

Not all future entities exist in schema v1. Add each when its owning phase has a tested contract; do not present a placeholder as implemented functionality.

## Provenance and lifecycle

Every derived record references repository/file identity and source path, content hash, parent archive, extraction depth, parser/tool + version, processing timestamp, pipeline version, errors/fallbacks and confidence. Derivations are versioned; deduplication creates relationships, never source deletion. A claim should carry its evidence locator and distinguish visible fact, parsed fact and inference.

## Safety

Enable SQLite foreign keys on every connection; use transactions for state transitions; index identity/status/hash columns; use FTS5 only when available and retain a non-FTS fallback. Never store credentials from source material. Limit extracted content size and store large canonical payloads as filesystem objects with digest references.
