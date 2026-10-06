# Memory Architecture

Persist structured memory and portable Markdown, with SQLite authoritative for querying and lifecycle. Separate conversations/messages, summaries, user preferences, verified project facts, decisions, tasks, successful/failed solutions, research, tools/models, resources and system configuration. Each record carries provenance, timestamp, trust/confidence, scope, sensitivity, expiry/supersession and source references.

Do not place the entire database in an LLM context. Retrieve by explicit scope and budget; filter sensitive/unverified material; label retrieved text as untrusted data; include source links and count omissions. Local lexical search works without models or network. Embeddings are an optional, replaceable index with declared identity and rebuild path.

Historical knowledge imports are legacy records with original source path, import date, transform and confidence. Conflicts are linked and flagged; older content never silently overwrites newer verified facts. Secret screening precedes import.
