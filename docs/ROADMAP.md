# Roadmap

1. **Audit/state:** evidence-based historical audit, machine inventory, task/control plane.
2. **Corpus identity:** stable IDs, recursive file manifest, checksums, MIME/signatures, completeness reconciliation.
3. **Safe extraction:** bounded archive/package expansion and durable retry/error journal.
4. **Knowledge conversion:** parsers, source structure, docs/media/OCR metadata, faithful Markdown records and provenance (bounded UTF-8 text parser v3 implemented; 1,243/192,186 extracted outputs have parser state as of 2026-10-06; full corpus and non-text parsers pending).
5. **Storage/search:** per-item/global SQLite, FTS, duplicate/fork relationships, verified counts.
6. **Legacy knowledge:** secret-screened, provenance-preserving import and conflict detection.
7. **Research/memory:** local durable retrieval/memory first; optional resilient background research.
8. **Provider layer:** capability registry, health checks, local provider support and tested fallbacks; Ollama optional.
9. **Tools/agent runtime:** permissions, approvals, durable tasks, verification, recovery and modular agents.
10. **User surfaces:** CLI then API, web, VS Code against one service contract.
11. **Optional modalities/integrations:** browser/computer, voice, vision, MCP/A2A, media.
12. **Operations:** doctor, service supervision, backups, upgrade path, security and production audit.

Each stage exits only on measured tests and a persisted state checkpoint; later interfaces must not precede stable provider/tool/auth contracts.
