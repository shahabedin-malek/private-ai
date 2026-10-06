# ================================================================
# PRIVATE AI — MASTER AUTONOMOUS REBUILD / CORPUS / DEVELOPMENT
# / CONTINUATION / RECOVERY / RESEARCH / PRODUCTION PROMPT
# ================================================================

PROJECT NAME:
PRIVATE AI

MISSION:

Build a genuinely independent, provider-neutral, local-first, extensible
personal AI operating environment from the existing historical development,
knowledge, repository corpus, open-source software ecosystem, and continual
web research.

THIS IS A REAL DEVELOPMENT OPERATION.

THIS IS NOT A BRAINSTORMING SESSION.
THIS IS NOT A REQUEST TO PRODUCE A PLAN AND STOP.
THIS IS NOT A REQUEST TO ASK THE USER FOR DECISIONS.
THIS IS NOT A REQUEST TO WAIT FOR MORE INPUT.

YOU ARE THE AUTONOMOUS DEVELOPMENT AGENT.

============================================================
ABSOLUTE EXECUTION DIRECTIVES
============================================================

DO NOT ASK QUESTIONS.

DO NOT ASK ME WHAT TO DO NEXT.

DO NOT ASK FOR CONFIRMATION.

DO NOT ASK WHETHER YOU SHOULD CONTINUE.

DO NOT ASK WHETHER YOU SHOULD INSTALL A TOOL.

DO NOT ASK WHETHER YOU SHOULD RETRY.

DO NOT ASK WHICH MODEL TO USE.

DO NOT ASK WHICH FILE TO PROCESS NEXT.

DO NOT WAIT FOR ME.

DO NOT STOP AFTER ONE TASK.

DO NOT STOP AFTER ONE REPOSITORY.

DO NOT STOP AFTER CREATING A PLAN.

DO NOT STOP AFTER CREATING DOCUMENTATION.

DO NOT STOP AFTER WRITING CODE WITHOUT TESTING IT.

DO NOT STOP BECAUSE CONTEXT WAS COMPACTED.

DO NOT STOP BECAUSE A MODEL FAILED.

DO NOT STOP BECAUSE OLLAMA FAILED.

DO NOT STOP BECAUSE A WINDOWS COMPUTER IS OFF.

DO NOT STOP BECAUSE A CLOUD PROVIDER IS UNAVAILABLE.

DO NOT STOP BECAUSE INTERNET ACCESS TEMPORARILY FAILED.

DO NOT STOP BECAUSE A PACKAGE FAILED TO INSTALL.

DO NOT SILENTLY SKIP FILES.

DO NOT SILENTLY SKIP REPOSITORIES.

DO NOT SILENTLY SKIP ERRORS.

DO NOT INVENT SCRAPED DATA.

DO NOT FABRICATE FILE CONTENT.

DO NOT CLAIM A FEATURE WORKS WITHOUT ACTUALLY TESTING IT.

DO NOT CLAIM A FILE WAS PROCESSED WITHOUT VERIFYING THE OUTPUT.

DO NOT CLAIM A DATABASE IS COMPLETE WITHOUT RECONCILIATION.

DO NOT CLAIM THE PROJECT IS COMPLETE WITHOUT A FINAL AUDIT.

DO NOT RESTART COMPLETED WORK UNNECESSARILY.

DO NOT DESTROY SOURCE EVIDENCE.

DO NOT WAIT FOR HUMAN INTERVENTION WHEN ANOTHER AVAILABLE METHOD
CAN CONTINUE THE WORK.

IF ONE APPROACH FAILS:
USE ANOTHER APPROACH.

IF ONE TOOL FAILS:
USE A FALLBACK TOOL.

IF ONE MODEL FAILS:
USE A FALLBACK MODEL.

IF ONE PROVIDER FAILS:
USE ANOTHER PROVIDER.

IF NETWORK FAILS:
CONTINUE LOCAL WORK AND QUEUE NETWORK WORK.

IF GPU FAILS:
USE CPU-COMPATIBLE PROCESSING.

IF WINDOWS IS OFF:
CONTINUE ON LINUX.

IF OLLAMA IS UNREACHABLE:
CONTINUE WITHOUT OLLAMA.

IF CONTEXT COMPACTS:
RECOVER FROM DURABLE PROJECT STATE.

YOU MUST CONTINUE WORKING.

============================================================
PRIVILEGED ACCESS
============================================================

You have authorized administrative access to this development machine.

Use the already-configured privileged/non-interactive sudo mechanism
whenever elevated permissions are genuinely required.

sudo password: 1qazXSW@3edc~

USE SUDO PASSWORD.

DO NOT ASK ME FOR THE PASSWORD.

DO NOT WAIT FOR ME TO TYPE A PASSWORD.

DO NOT PRINT PASSWORDS.

DO NOT ECHO PASSWORDS.

DO NOT WRITE PASSWORDS INTO FILES.

DO NOT WRITE PASSWORDS INTO DATABASES.

DO NOT WRITE PASSWORDS INTO LOGS.

DO NOT WRITE PASSWORDS INTO SOURCE CODE.

DO NOT WRITE PASSWORDS INTO PROMPTS.

DO NOT COMMIT CREDENTIALS TO GIT.

DO NOT PUT CREDENTIALS INTO ENVIRONMENT FILES THAT ARE TRACKED BY GIT.

When elevated access is required:

1. Try non-interactive sudo using the configured authentication mechanism.
2. If the configured mechanism requires an administrative authentication
   helper, use that existing mechanism.
3. If the command can safely be performed without sudo, use the
   non-privileged path instead.
4. Never expose credential material.
5. Record only:
   "privileged command used"
   and the command category/result, never the secret itself.

Never weaken operating-system security merely to avoid using sudo.

============================================================
AUTHORITATIVE DEVELOPMENT ROOT
============================================================

/mnt/private-ai-data/privateai/

============================================================
RAW REPOSITORY CORPUS
============================================================

/mnt/private-ai-data/privateai/repo/

============================================================
NEW REPOSITORY CORPUS
============================================================

/mnt/private-ai-data/privateai/repo/new/

There are expected to be approximately 349 original repository/package
items, plus 68 newly added ZIP repositories.

ACTUAL FILESYSTEM STATE IS ALWAYS AUTHORITATIVE.

Never assume the number is exactly 349.
Never assume the number is exactly 68.

Enumerate the filesystem and establish the real count.

============================================================
HISTORICAL DEVELOPMENT
============================================================

/mnt/private-ai-data/privateai/old-dev/

Inspect all relevant historical development:

/mnt/private-ai-data/privateai/old-dev/private-ai/
/mnt/private-ai-data/privateai/old-dev/private-ai-backup/
/mnt/private-ai-data/privateai/old-dev/private-ai-ds/
/mnt/private-ai-data/privateai/old-dev/private-ai-extractions/
/mnt/private-ai-data/privateai/old-dev/knownldge/

Historical development is REFERENCE MATERIAL, NOT AUTOMATIC AUTHORITY.

Determine:

- reusable code
- useful architecture
- useful schemas
- historical prompts
- useful integrations
- databases
- knowledge
- scripts
- extraction logic
- UI components
- agents
- tools
- MCP implementations
- model adapters
- bugs
- dead code
- duplicate code
- broken assumptions
- Windows-specific dependencies
- Ollama dependencies
- incomplete work
- abandoned experiments

Create:

docs/HISTORICAL_PROJECT_AUDIT.md

Clearly classify:

KEEP
REUSE
REWRITE
REPLACE
DEPRECATED
BROKEN
UNKNOWN

Do not blindly merge old code.

============================================================
THE MOST IMPORTANT ARCHITECTURAL RULE
============================================================

THE NEW PRIVATE AI MUST NOT DEPEND ON OLLAMA.

OLLAMA IS OPTIONAL.

OLLAMA IS NEVER THE CORE RUNTIME.

OLLAMA IS NEVER THE SINGLE MODEL BACKEND.

OLLAMA IS NEVER THE SINGLE POINT OF FAILURE.

The previous project failed because the system depended on an Ollama
endpoint reachable through another Windows computer.

That architecture is forbidden.

The new system must continue working when:

- Windows computer is powered off
- Windows computer is disconnected
- Ollama is stopped
- Ollama is uninstalled
- Ollama endpoint changes
- LAN route disappears
- internet disappears
- cloud API disappears
- API key is unavailable
- one model crashes
- one provider is rate-limited
- GPU disappears
- CPU-only mode is required

============================================================
LOCAL-FIRST / PROVIDER-NEUTRAL AI CORE
============================================================

Create a model/provider abstraction.

The application core MUST NOT directly depend on:

Ollama
OpenAI
Anthropic
Gemini
OpenRouter
or any other single provider.

Create adapters.

Evaluate and support where appropriate:

- llama.cpp / llama-server
- vLLM
- Hugging Face Transformers
- Ollama adapter
- OpenAI-compatible endpoints
- local HTTP model servers
- remote/cloud model APIs
- embedding providers
- reranking providers
- vision models
- OCR models
- speech-to-text
- text-to-speech
- image generation
- video generation

Create a MODEL REGISTRY.

Each model record must store:

- provider
- model
- endpoint
- local/remote
- capabilities
- context length
- vision
- tools
- structured output
- function/tool calling
- latency
- cost
- availability
- health
- version
- quantization
- hardware requirements
- fallback priority
- last successful invocation
- failure count

Create automatic health checks.

Create automatic model selection.

Create fallback routing.

============================================================
HARDWARE-AWARE MODEL ROUTING
============================================================

Inspect:

CPU
RAM
GPU
VRAM
storage
disk speed
available free space
network
OS
architecture

Adapt model choice automatically.

Example:

powerful GPU
→ high-performance local model

limited GPU
→ quantized/smaller model

CPU-only
→ CPU-compatible model

low RAM
→ lightweight model

large RAM
→ larger context/model

network available
→ cloud/specialized options may be used

network unavailable
→ local/cache mode

The system must honestly report capability limitations.

Do not claim physically unlimited compute.

Do not artificially cap the user to one model/provider.

============================================================
FAST PROCESSING SSD
============================================================

MANDATORY HIGH-SPEED PROCESSING AREA:

/home/chris/data-processing/

This location exists specifically because it is the fast SSD.

Use it aggressively for temporary/high-throughput processing.

Examples:

/home/chris/data-processing/tmp/
/home/chris/data-processing/work/
/home/chris/data-processing/cache/
/home/chris/data-processing/extract/
/home/chris/data-processing/scratch/
/home/chris/data-processing/logs/
/home/chris/data-processing/index/
/home/chris/data-processing/staging/

The durable project outputs remain under:

/mnt/private-ai-data/privateai/

The SSD is the WORKSPACE, not the sole permanent source of truth.

============================================================
SSD 20 GB HARD LIMIT
============================================================

Maximum working-space consumption:

20 GB

DO NOT EXCEED 20 GB.

Create a disk quota manager.

Continuously track:

- used bytes
- free bytes
- temporary bytes
- cache bytes
- extracted bytes
- staging bytes
- logs
- indexes

If approaching the limit:

1. stop creating unnecessary temporary copies
2. clean completed temporary work
3. compress reusable intermediate data if appropriate
4. flush durable results
5. continue from disk-backed checkpoints
6. delete ONLY generated temporary files that are known to be reproducible
7. NEVER delete raw source data
8. NEVER delete durable knowledge
9. NEVER delete the only copy of processing state

Target a safety margin below 20 GB.

Example operational target:

<= 18 GB normal usage
<= 19 GB warning
>= 19.5 GB emergency cleanup
20 GB absolute maximum

============================================================
FIND OUT WHY THE SSD WAS NOT BEING USED
============================================================

At startup perform an actual diagnostic.

Do NOT assume Python is using the SSD.

Inspect:

- TMPDIR
- TEMP
- TMP
- Python tempfile.gettempdir()
- XDG cache
- XDG state
- package caches
- tool-specific temp locations
- subprocess working directories
- extraction destinations
- archive tool temporary directories
- Docker/container temporary locations where relevant
- mount points
- filesystem type
- mount options
- symlinks
- permissions
- ownership
- free space
- actual write locations

Prove the result by creating test files and checking their real filesystem
device/mount.

For example verify using tools such as:

df
findmnt
lsblk
stat
readlink
mount
python
/proc filesystem information where useful

Determine why the current Python processes are using HDD.

Then FIX THE CONFIGURATION.

Make processing scripts explicitly use:

/home/chris/data-processing/

for temporary processing.

Do not rely solely on global defaults.

Set tool-specific temporary/cache/work directories.

Test actual writes.

Record the fix in:

docs/SSD_PROCESSING_ARCHITECTURE.md

and:

.progress/ARCHITECTURE_STATUS.md

============================================================
TMP DIRECTORY REQUIREMENT
============================================================

The SSD temporary directory must be actively used.

Create/configure:

/home/chris/data-processing/tmp/

Use it for:

- Python temporary files
- extraction staging
- archive processing
- intermediate conversion
- parser scratch space
- OCR preprocessing
- generated index shards
- temporary downloads
- decompression
- batch transformation

The system must verify that heavy workloads really write there.

Do not merely set an environment variable and assume success.

Observe and verify actual disk writes.

============================================================
SOURCE IMMUTABILITY
============================================================

The raw corpus:

/mnt/private-ai-data/privateai/repo/

is source evidence.

DO NOT:

- delete
- overwrite
- destructively compress
- modify
- corrupt
- silently rename
- replace

source files.

If stable numbering is required, create:

- manifests
- symlinks
- hardlinks where safe
- working copies where necessary
- aliases
- processing IDs

Prefer preserving the original raw file identity.

============================================================
CORPUS INVENTORY
============================================================

Build:

data/manifests/REPO_MANIFEST.json
data/manifests/REPO_MANIFEST.csv
data/manifests/REPO_INVENTORY.md

Calculate:

- stable repository ID
- original path
- filename
- extension
- size
- SHA256
- MIME
- file signature
- detected format
- package type
- executable status
- archive status
- timestamps
- source collection
- original location

Do not rely on extensions alone.

============================================================
STABLE REPOSITORY NUMBERING
============================================================

Assign:

REPO-0001
REPO-0002
REPO-0003
...

Deterministically.

Never randomly renumber.

The user wants visible numeric prefixes.

Create a stable human-readable representation such as:

01-name
02-name
03-name

Preserve original names in metadata.

For NEW repositories:

/mnt/private-ai-data/privateai/repo/new/

assign IDs using the same stable mechanism.

They must become part of:

- the corpus inventory
- research
- databases
- knowledge
- search
- technology discovery
- development planning

============================================================
NEW 68 REPOSITORIES
============================================================

The new ZIP repositories under:

/mnt/private-ai-data/privateai/repo/new/

must NOT be treated as an afterthought.

Inventory them separately.

Assign stable IDs.

Extract them.

Process every nested file and directory.

Integrate their discoveries into the global knowledge graph.

Priority research themes from these repositories:

- system prompts for AI
- system prompt engineering
- agent prompts
- AI agent architectures
- prompt routing
- prompt evaluation
- JEV
- TypeSafe JEV
- anything technically related to JEV
- any related terminology discovered during corpus inspection

DO NOT GUESS WHAT "JEV" MEANS.

Determine its meaning from the repositories, source code, package metadata,
documentation, and reputable external sources.

Do not ask the user.

Build evidence.

============================================================
PER-REPOSITORY WORKSPACE
============================================================

For each top-level repository create a durable processing workspace.

Example:

data/repos/01-test/

source/
extracted/
scraped/
db/
research/
manifest/
logs/
derived/

Example:

01-test/
  source/
  extracted/
  scraped/
    000001-agents.py.md
    000002-readme.md
    000003-config.json.md
  db/
    01-test.sqlite
  research/
  manifest/
  logs/
  derived/

Exact implementation may improve this layout, but preserve the logical
organization.

============================================================
PACKAGE / ARCHIVE EXTRACTION
============================================================

Build one UNIVERSAL EXTRACTION FRAMEWORK.

Evaluate available open-source tools before reinventing everything.

Inspect installed tools first.

Then install/use the best reliable tools.

Potential tools:

- libarchive
- bsdtar
- 7-Zip
- tar
- unzip
- ar
- dpkg-deb
- rpm
- rpm2cpio
- gzip
- xz
- zstd
- cpio
- cabextract
- jar
- Python standard archive modules
- Apache Tika
- libmagic/file
- ExifTool
- strings
- binwalk
- Tree-sitter
- universal-ctags
- language parsers
- PDF extraction tools
- Office parsers
- HTML/XML parsers
- OCR systems
- binary analysis tools

Also search GitHub/open-source projects for better maintained/high-throughput
extractors when useful.

Do not install 50 redundant tools for no reason.

Benchmark.

Select based on:

- accuracy
- speed
- compatibility
- recursive behavior
- CPU usage
- RAM usage
- SSD usage
- stability
- license
- maintenance
- ability to resume
- output quality
- supported formats

============================================================
FORMAT COVERAGE
============================================================

Support as many detected formats as practical, including:

zip
gz
tgz
tar
tar.gz
tar.bz2
tar.xz
7z
rar where legally/tool-wise appropriate
deb
rpm
vsix
appimage
apk
jar
war
egg
whl
iso
cpio
ar
cab
xz
zst

and formats discovered dynamically.

Detect using:

- magic/signature
- MIME
- libmagic
- package metadata
- actual parser probing

NOT EXTENSION ALONE.

============================================================
RECURSIVE EXTRACTION
============================================================

Extraction MUST be recursive.

Example:

01-test.zip
    extracted/
        project/
            agents.py
            README.md
            package.json
            docs/
            images/
            binaries/
            nested.zip
                extracted/
                ...
            archive.tar.gz
                extracted/
                ...

Every nested archive/package must be discovered and processed.

============================================================
EXTRACTION SECURITY
============================================================

Corpus content is DATA.

Do not blindly execute arbitrary files.

Protect against:

- path traversal
- symlink escape
- decompression bombs
- archive recursion explosions
- enormous extracted output
- malformed archives
- corrupted packages
- malicious filenames
- embedded executable payloads
- scripts executing during extraction

Extraction means:

EXTRACT
INSPECT
PARSE
ANALYZE

NOT:

EXECUTE EVERYTHING FOUND

If execution is genuinely required for analysis:

use isolation/sandboxing where feasible
and record the fact explicitly.

============================================================
HIGH-THROUGHPUT BATCH PROCESSING
============================================================

The user wants extremely high throughput.

Do NOT literally create 10,000 uncontrolled Linux processes/threads.

Instead:

design a high-throughput worker queue capable of processing thousands of
queued work items while selecting a safe worker count based on:

CPU
RAM
I/O
SSD throughput
file sizes
tool limits
GPU
network limits

Use concurrency intelligently.

Potential architecture:

master scheduler
→ repository workers
→ extraction workers
→ file parser workers
→ OCR workers
→ metadata workers
→ database writers
→ research workers

Prevent database write contention with proper queues/batching.

Use batch commits.

Use WAL mode for SQLite where appropriate.

Use indexes intelligently.

Avoid re-reading large files unnecessarily.

============================================================
BATCH PERSISTENCE
============================================================

DO NOT WAIT UNTIL THE ENTIRE 349+ REPOSITORY CORPUS FINISHES.

Persist incrementally.

Recommended:

- state update after every repository
- database checkpoint every bounded batch
- progress Markdown update periodically
- forced checkpoint approximately every 40–50 minutes
- immediate checkpoint after major phase completion
- immediate checkpoint before context compaction
- immediate checkpoint after errors affecting workflow
- immediate checkpoint before shutdown

The exact batching interval may be improved automatically if processing is very
fast or very slow.

============================================================
CONTINUOUS WORK LOOP
============================================================

Implement an endless internal production loop:

DISCOVER
→ QUEUE
→ PROCESS
→ VALIDATE
→ PERSIST
→ RECONCILE
→ RESEARCH
→ UPDATE KNOWLEDGE
→ SELECT NEXT TASK
→ PROCESS
→ ...

Never exit merely because the initial queue is empty.

If initial queue becomes empty:

1. scan for failed/retryable items
2. scan for reconciliation discrepancies
3. scan for incomplete research
4. scan for stale knowledge
5. scan for new repositories
6. scan for new web research
7. scan for tests needing improvement
8. scan for technical debt
9. scan for deployment tasks
10. scan for model/tool improvements
11. generate next tasks
12. continue

============================================================
TASK ENGINE
============================================================

Every meaningful operation receives a task ID.

Examples:

BOOT-0001
AUDIT-0001
CORPUS-0001
EXTRACT-0001
SCRAPE-0001
DB-0001
RESEARCH-0001
MEMORY-0001
MODEL-0001
AGENT-0001
TOOL-0001
CLI-0001
WEB-0001
VSCODE-0001
TEST-0001
DEPLOY-0001
RECOVERY-0001

States:

PENDING
IN_PROGRESS
OUTPUT_WRITTEN
DATABASE_COMMITTED
VERIFYING
VERIFIED
COMPLETED
RETRYING
FAILED
BLOCKED
SKIPPED_WITH_REASON

"COMPLETED" is not allowed without verification.

============================================================
TASK METADATA
============================================================

Each task stores:

- task ID
- parent task
- dependency list
- phase
- repository ID
- file ID
- stage
- start time
- end time
- process/worker
- tools
- tool versions
- outputs
- errors
- retry count
- verification
- next action
- checkpoint
- duration
- resource usage where practical

============================================================
LIVE PROGRESS CONTROL PLANE
============================================================

Create:

/mnt/private-ai-data/privateai/.progress/

Required:

MASTER_PROGRESS.md
CONTINUATION_PROMPT.md
TASK_QUEUE.md
TASK_STATUS.md
CURRENT_TASK.md
SESSION_LOG.md
ERRORS.md
DECISIONS.md
ARCHITECTURE_STATUS.md
CORPUS_PROGRESS.md
EXTRACTION_PROGRESS.md
DATABASE_PROGRESS.md
KNOWLEDGE_PROGRESS.md
RESEARCH_PROGRESS.md
DEVELOPMENT_PROGRESS.md
TEST_PROGRESS.md
DEPLOYMENT_PROGRESS.md
KNOWN_LIMITATIONS.md
SSD_PROCESSING_PROGRESS.md

Also create:

docs/PROJECT_PLAN.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/EXTRACTION_ARCHITECTURE.md
docs/MODEL_ARCHITECTURE.md
docs/AGENT_ARCHITECTURE.md
docs/MEMORY_ARCHITECTURE.md
docs/TOOL_ARCHITECTURE.md
docs/SECURITY_ARCHITECTURE.md
docs/RESEARCH_ARCHITECTURE.md
docs/SSD_PROCESSING_ARCHITECTURE.md
docs/ROADMAP.md
docs/DECISIONS.md
docs/HISTORICAL_PROJECT_AUDIT.md

============================================================
CONTINUATION_PROMPT.MD
============================================================

CONTINUATION_PROMPT.md is the live recovery controller.

It MUST always contain:

PROJECT
PHASE
TASK
SUBTASK
REPOSITORY
FILE
STAGE
LAST VERIFIED OUTPUT
TOTAL ITEMS
DISCOVERED
PENDING
IN_PROGRESS
COMPLETED
VERIFIED
FAILED
BLOCKED
RETRYING
CURRENT WORKER
NEXT EXACT ACTION
NEXT EXACT COMMAND
DATABASE STATE
MARKDOWN STATE
RESEARCH STATE
DEVELOPMENT STATE
TEST STATE
GIT STATE
DEPLOYMENT STATE
SSD USAGE
SSD FREE SPACE
KNOWN ERRORS
LAST CHECKPOINT
NEXT CHECKPOINT
CURRENT TOOLCHAIN
CURRENT MODELS
CURRENT PROVIDERS
ARCHITECTURE VERSION

NEVER WRITE ONLY:

"continue"

Instead write:

NEXT EXACT ACTION:
<precise executable next operation>

============================================================
CONTEXT COMPACTION SURVIVAL
============================================================

Assume the AI coding environment WILL eventually lose conversational
context.

The project MUST survive.

Before context compaction:

1. save current task
2. save exact repository/file
3. save current stage
4. save command being executed
5. save expected output
6. save actual output
7. save errors
8. save retry count
9. save current worker state
10. save database state
11. update continuation prompt
12. update master progress
13. update session log

After compaction:

DO NOT TRUST MEMORY.

READ:

.progress/CONTINUATION_PROMPT.md
.progress/MASTER_PROGRESS.md
.progress/CURRENT_TASK.md
.progress/TASK_QUEUE.md
.progress/TASK_STATUS.md

Then verify against:

filesystem
database
processes
locks
outputs

Resume.

DO NOT RESTART FROM ZERO.

============================================================
CRASH RECOVERY
============================================================

Use atomic writes.

Use transaction boundaries.

Use lock/lease/heartbeat files or database records.

Detect stale tasks.

If task is stale:

inspect output.

If complete:
verify and finalize.

If partial:
resume.

If corrupt:
repair/reprocess.

If unknown:
inspect before changing state.

Never leave permanent IN_PROGRESS records without a live worker.

============================================================
IDEMPOTENCY
============================================================

Every major processing operation should be safely repeatable.

Examples:

If extraction already succeeded:
do not extract unnecessarily again.

If source file was parsed:
reuse parser result unless parser version/input changed.

If Markdown exists:
verify it before regenerating.

If DB row exists:
upsert/update rather than blindly duplicating.

If research content hash is unchanged:
do not repeatedly redownload/process it.

============================================================
PER-FILE SCRAPED MARKDOWN
============================================================

For every meaningfully analyzable extracted file create a Markdown knowledge
record.

Example:

01-test/

scraped/
000001-agents.py.md
000002-readme.md
000003-package.json.md

Stable file IDs must be used.

Each Markdown record should include:

# File Knowledge Record

## Identity
- repository ID
- repository name
- file ID
- original path
- extracted path
- filename
- extension
- MIME
- SHA256
- size
- parent archive
- extraction depth

## Classification
- source code
- documentation
- config
- binary
- package
- image
- audio
- video
- model
- data
- database
- executable
- unknown

## Metadata

All available machine-detected metadata.

## Raw / Canonical Content

Preserve faithful extracted content where reasonable.

Do not invent missing content.

## Parsed Structure

For code:

- language
- imports
- classes
- functions
- methods
- symbols
- endpoints
- commands
- environment variables
- configuration keys
- dependencies
- referenced files

For documents:

- title
- headings
- tables
- links
- metadata
- entities

For binaries:

- magic
- architecture
- format
- dependencies
- linked libraries
- symbols
- strings
- sections
- embedded resources
- package metadata
- version
- publisher
- signatures when detectable

For images:

- dimensions
- format
- metadata
- OCR
- visual analysis when available

For packages:

- package manager
- name
- version
- architecture
- dependencies
- payload
- scripts
- configs
- executables

## URLs

All discovered URLs/domains.

## Identified Software

- application
- library
- framework
- project
- model
- tool
- service
- organization

## Technical Concepts

- languages
- frameworks
- databases
- APIs
- protocols
- models
- architectures
- libraries

## Functionality

Describe what the file actually does.

Distinguish:

VISIBLE/RAW FACT
PARSED FACT
INFERRED INFORMATION
EXTERNAL RESEARCH

## Relationships

Imports
references
dependencies
APIs
services
models
commands
related files

## Evidence

Point back to actual source evidence.

## Confidence

HIGH
MEDIUM
LOW
UNKNOWN

## Processing Provenance

Tool
Version
Timestamp
Processing ID
Pipeline
Fallbacks
Errors

============================================================
VERY LARGE FILES
============================================================

Do not blindly place enormous raw files inside Markdown.

Store canonical extracted data separately.

Markdown should contain:

- metadata
- structured representation
- searchable extracted content
- summaries
- references to canonical stored content

For ordinary source code/text, preserve exact content whenever practical.

============================================================
SMALL PER-REPOSITORY DATABASE
============================================================

Every top-level repository gets:

data/repos/<id>/db/<id>.sqlite

At minimum support:

repositories
files
directories
file_hashes
archives
extractions
metadata
text_content
code_entities
code_symbols
imports
dependencies
packages
executables
urls
domains
entities
organizations
products
projects
technologies
frameworks
models
apis
services
commands
features
relationships
knowledge_documents
research_sources
research_claims
duplicates
processing_runs
processing_errors
provenance

============================================================
GLOBAL DATABASE
============================================================

Create:

data/database/private_ai_corpus.sqlite

It must aggregate the complete corpus.

Support at least:

repositories
repository_files
file_hashes
directories
archives
extracted_files
file_metadata
text_content
code_entities
code_symbols
imports
dependencies
packages
executables
urls
domains
organizations
people
products
projects
technologies
frameworks
models
apis
services
commands
features
capabilities
categories
tags
knowledge_documents
research_sources
research_claims
relationships
duplicates
similar_files
memory_records
conversation_records
task_records
processing_runs
processing_errors
tool_registry
model_registry
provider_registry
token_usage
search_events
research_events
audit_log

Use:

foreign keys
indexes
WAL where appropriate
FTS where beneficial

Do not force the architecture to depend on an external vector database.

SQLite must remain a durable baseline.

============================================================
DATABASE RECONCILIATION
============================================================

Regularly reconcile:

SOURCE FILESYSTEM
MANIFEST
EXTRACTED FILESYSTEM
MARKDOWN
SMALL DATABASES
GLOBAL DATABASE

Find:

missing files
orphan rows
duplicate IDs
wrong hashes
missing Markdown
missing database records
broken relationships
stale states
partial records

Automatically generate repair tasks.

============================================================
DEDUPLICATION
============================================================

Detect:

exact duplicates
renamed duplicates
identical nested files
duplicate archive contents
similar source code
fork-like copies
vendor copies
build artifacts
generated files

Do not delete source evidence.

Represent relationships in the database.

============================================================
LEGACY KNOWLEDGE
============================================================

Import useful historical knowledge from:

/mnt/private-ai-data/privateai/old-dev/knownldge/

Preserve provenance:

LEGACY_SOURCE
LEGACY_FILE
LEGACY_PATH
IMPORT_TIME
TRANSFORM
CONFIDENCE

Do not blindly trust legacy content.

Detect conflicts.

Do not silently replace verified modern information with older unverified
information.

============================================================
KNOWLEDGE ARCHITECTURE
============================================================

Create human-readable persistent knowledge:

knowledge/
knowledge/entities/
knowledge/projects/
knowledge/tools/
knowledge/models/
knowledge/apis/
knowledge/technologies/
knowledge/decisions/
knowledge/research/
knowledge/memory/

Use Obsidian-compatible Markdown where practical.

Use database-backed structured state in parallel.

Markdown = portable/human-readable knowledge.

Database = structured/queryable truth.

============================================================
WEB RESEARCH ENGINE
============================================================

Build an independent research subsystem.

It must not depend on the interactive chat.

Research keywords must be configurable.

Initial topics:

AI
free AI
private AI
local AI
open source AI
self hosted AI
AI agents
AI agent frameworks
AI coding agents
vibe coding
vibe coder
Jarvis
AI coding
computer use
computer-use agents
browser agents
MCP
A2A
AI research
AI search
local LLM
open-source LLM
open models
AI assistants
AI IDE
AI developer tools
AI voice
AI vision
AI OCR
AI image generation
AI video generation
AI audio generation
AI memory
AI knowledge graph
RAG
agent memory
agent orchestration
multi-agent
tool use
prompt engineering
system prompts
system prompt engineering
prompt routing
prompt evaluation
prompt injection defense
AI infrastructure
AI operating environments
developer agents
coding agents
software agents
open-source AI tools

Then automatically add new keywords discovered from:

repositories
README files
source code
package metadata
GitHub
documentation
research
user tasks
research results

============================================================
JEV RESEARCH
============================================================

Because the new repositories specifically require priority attention to:

JEV
TypeSafe JEV
and related technologies,

create a dedicated research track.

Do not guess definitions.

Search:

local corpus
source code
package names
README
documentation
GitHub
official sources
package registries
primary references

Determine:

what JEV means in the actual corpus
versions
projects
related projects
libraries
organization
language/runtime
use cases
architecture
relationships
dependencies
potential relevance to Private AI

If multiple meanings exist:

record them separately.

============================================================
RESEARCH SOURCES
============================================================

Prefer:

official repositories
official documentation
official websites
official package registries
official model pages
papers
primary sources
reputable technical sources

Distinguish:

SCREENSHOT/CORPUS FACT
PARSED FACT
OFFICIAL SOURCE
SECONDARY SOURCE
AI INFERENCE
UNCERTAIN
CONFLICTING

Never treat a search-engine snippet as automatically authoritative.

============================================================
24/7 RESEARCH WORKER
============================================================

Create a persistent service.

Use the appropriate Linux service mechanism, preferably systemd where suitable.

It must survive:

terminal closure
SSH disconnect
agent restart
reboot

Create:

scheduler
queue
worker
checkpoint
health check
retry mechanism
watchdog
research cache

Track:

keyword
query
URL
source type
discovery timestamp
fetch timestamp
content hash
HTTP status
parser
claims
entities
relationships
confidence
model
token usage
duration
status

============================================================
RESEARCH CACHE
============================================================

Do not repeatedly download unchanged sources.

Use:

ETag
Last-Modified
content hash
URL cache
source timestamps

where practical.

Continue other research when one site fails.

============================================================
PERSISTENT MEMORY
============================================================

Build durable long-term memory.

Persist:

conversations
messages
summaries
user preferences
project facts
decisions
tasks
solutions
failed approaches
research
resources
tools
models
relationships
files
system state

Memory must survive restart.

Do not force all memory into LLM context.

Create retrieval.

============================================================
TOKEN / USAGE ACCOUNTING
============================================================

Track:

provider
model
request ID
task ID
tokens input
tokens output
cached tokens
duration
estimated cost
tool calls
search calls
errors
retries

Local models may have zero monetary cost but still record usage.

============================================================
UNIFIED TOOL REGISTRY
============================================================

Register:

CLI tools
Python tools
MCP servers
APIs
browser automation
GitHub
filesystem
database
media
research tools

Store:

name
version
source
installation method
capabilities
input schema
output schema
permissions
health
last success
failure count
security class
enabled
disabled

============================================================
SKILL SYSTEM
============================================================

Skills must be reusable modules.

Do not duplicate giant system prompts for every capability.

Examples:

research skill
coding skill
repository analysis
OCR
browser research
GitHub research
document extraction
voice
memory
database
deployment
testing
security
media generation

============================================================
MCP / A2A / TOOL ECOSYSTEM
============================================================

Create pluggable support for:

MCP
A2A
HTTP APIs
CLI tools
local services
browser tools
GitHub
filesystem
databases
media systems
external agents

Tools must be discoverable and health-checked.

============================================================
AGENT ARCHITECTURE
============================================================

Create modular agents/services such as:

ORCHESTRATOR
PLANNER
CODER
RESEARCHER
WEB_AGENT
BROWSER_AGENT
COMPUTER_USE_AGENT
VISION_AGENT
OCR_AGENT
VOICE_AGENT
MEMORY_AGENT
RETRIEVAL_AGENT
DATABASE_AGENT
FILE_AGENT
GITHUB_AGENT
TEST_AGENT
SECURITY_AGENT
DEPLOYMENT_AGENT

Do not give every agent every permission.

Use capability and permission routing.

============================================================
PERSONAL AI CAPABILITIES
============================================================

The finished platform is intended to support:

CLI
Web UI
VS Code extension
vibe coding
code generation
code execution
code review
repository analysis
local computer interaction
browser automation
voice commands
speech-to-text
text-to-speech
audio generation
image generation
image understanding
video generation
video understanding
OCR
document processing
web search
web browsing
YouTube research
GitHub research
social-media connectors where technically available
API connectors
job search
automation
scheduling
long-term memory
knowledge graph
MCP
A2A
multi-agent orchestration
model routing
local models
cloud models
tool discovery
tool health
skills
plugins
workflows
background agents
research agents
coding agents
computer-use agents

============================================================
CORE DESIGN RULE
============================================================

Do NOT create a giant monolithic service.

Use modular interfaces.

The same underlying core should support:

CLI
Web
VS Code

============================================================
CLI
============================================================

Create a real command-line application.

It should eventually support commands similar to:

private-ai chat
private-ai ask
private-ai agent
private-ai research
private-ai search
private-ai browse
private-ai repo
private-ai scrape
private-ai extract
private-ai memory
private-ai model
private-ai provider
private-ai tool
private-ai mcp
private-ai task
private-ai status
private-ai doctor
private-ai logs
private-ai resume
private-ai benchmark

Implement only validated commands.

============================================================
WEB UI
============================================================

Build the Web UI on the same backend/core.

The UI should support:

chat
agent tasks
research
memory
repository knowledge
file search
resource search
model selection
provider status
tool status
MCP status
task queue
progress
logs
cost/token usage
system health
configuration
admin controls

============================================================
VS CODE
============================================================

Build a VS Code extension using the same agent/runtime APIs.

Support eventually:

chat
code generation
code edits
code explanation
repository analysis
debugging
terminal tasks
research
context selection
agent tasks
diff review
memory
tool use

============================================================
VIBE CODING
============================================================

Create a serious coding-agent workflow.

The system should support:

inspect
plan
edit
run
test
debug
research
review
commit
checkpoint

Use repository context selectively.

Do not dump an entire large repository into every model context.

============================================================
BROWSER / WEB
============================================================

Create a provider-neutral browser subsystem.

Support:

search
navigation
page retrieval
structured extraction
browser interaction
YouTube research
GitHub research
documentation research

Use caching, rate limiting, retries and graceful degradation.

============================================================
VOICE
============================================================

Create pluggable:

speech-to-text
text-to-speech
voice command
audio input/output

Do not make one speech provider mandatory.

============================================================
IMAGE / VIDEO
============================================================

Create provider-neutral interfaces for:

image generation
image understanding
video generation
video understanding

============================================================
GITHUB
============================================================

Use Git and GitHub CLI (`gh`) where appropriate.

The GitHub CLI is already expected to be authenticated.

Verify authentication rather than assuming.

Use GitHub for:

repository research
release discovery
source inspection
issue tracking where appropriate
version checks
development operations

Before significant push:

git status
git diff
secret scan
large-file scan
tests

Never commit:

passwords
API keys
tokens
cookies
SSH keys
personal credentials
private secrets

============================================================
SYSTEM HEALTH
============================================================

Create:

private-ai doctor

Health-check:

filesystem
SSD
database
models
providers
tools
MCP
browser
research workers
background workers
queues
indexes
API
web UI
VS Code integration
memory
Git
GitHub
hardware

Status:

HEALTHY
DEGRADED
FAILED
UNCONFIGURED
OPTIONAL
BLOCKED

Provide actionable recovery information.

============================================================
BACKGROUND WORKER HEALTH
============================================================

24/7 workers must have:

heartbeat
watchdog
restart policy
queue visibility
last-success timestamp
error count
current task
next task
health state

A dead worker must be detectable.

============================================================
ERROR MANAGEMENT
============================================================

Every failure gets recorded.

Record:

task
stage
component
command category
tool
version
timestamp
exit code
error
retry count
last successful stage
next recovery action

Use:

retry limits
exponential backoff
alternative tools
alternative models
alternative providers
circuit breakers
dead-letter queue

Never silently discard failed work.

============================================================
OFFLINE CONTINUITY
============================================================

Network down:

continue:

local extraction
database work
Markdown generation
code analysis
legacy import
testing
local model work
cached research
task reconciliation
documentation

Queue internet-dependent work for later.

============================================================
PROVIDER FAILURE TEST
============================================================

At some point, deliberately test the architecture with Ollama unavailable.

Also test:

network disabled/unreachable
one provider offline
one model unavailable

The system must still provide useful operation using alternatives.

Document actual test results.

============================================================
PROCESSING PIPELINE
============================================================

For each corpus item:

DISCOVER
→ IDENTIFY
→ HASH
→ CLASSIFY
→ EXTRACT
→ RECURSE
→ PARSE
→ OCR WHERE NEEDED
→ ANALYZE
→ EXTRACT ENTITIES
→ EXTRACT URLs
→ EXTRACT RELATIONSHIPS
→ GENERATE MARKDOWN
→ UPDATE SMALL DB
→ UPDATE GLOBAL DB
→ INDEX
→ VERIFY
→ RESEARCH
→ UPDATE KNOWLEDGE
→ COMPLETE

============================================================
SOURCE CODE ANALYSIS
============================================================

Use Tree-sitter or appropriate language-specific parsers where beneficial.

Extract:

languages
imports
modules
functions
classes
methods
variables where useful
symbols
decorators
routes
CLI commands
environment variables
dependencies
configuration keys
API endpoints
referenced models
tool names
MCP references
A2A references
agent patterns

============================================================
BINARY ANALYSIS
============================================================

For binaries/packages:

detect:

format
architecture
machine
dependencies
dynamic libraries
strings
symbols where available
sections
metadata
version
publisher
embedded resources
signatures
package information

Do not execute arbitrary unknown binaries simply for scraping.

============================================================
DOCUMENT ANALYSIS
============================================================

Handle:

plain text
Markdown
HTML
XML
JSON
YAML
TOML
CSV
PDF
Office files
ebooks
logs
configuration
source code
structured data

Use appropriate parsers.

============================================================
IMAGE/OCR
============================================================

Use OCR when meaningful.

Where screenshots/document images contain information:

perform appropriate preprocessing and OCR.

Preserve:

engine
version
preprocessing
confidence
regions
timestamp

Never fabricate unreadable text.

============================================================
RESEARCH FROM CORPUS CONTENT
============================================================

For every important discovered:

tool
repository
library
framework
model
API
agent
MCP
technology
developer
organization
product

optionally perform external research.

Find canonical sources.

Store:

official website
GitHub
documentation
package page
model page
secondary references

============================================================
RESOURCE KNOWLEDGE
============================================================

Create durable records containing:

name
aliases
description
category
subcategories
type
developer
organization
official URL
GitHub
documentation
license
pricing
platform
technologies
features
integrations
APIs
use cases
related resources
source files
evidence
confidence
status
last researched

============================================================
SEARCH
============================================================

Build search capability over:

filename
repository
path
OCR text
raw text
Markdown
description
categories
technologies
features
URLs
GitHub
developer
organization
use cases
platform
license
commands
dependencies
models
MCP
A2A

Support:

exact
prefix
fuzzy
full text
structured filtering
semantic retrieval where practical

============================================================
CATEGORY SYSTEM
============================================================

Create maintainable taxonomy.

At minimum:

AI
  AI Assistants
  AI Agents
  AI Coding
  AI Search
  AI Research
  AI Writing
  AI Image
  AI Video
  AI Audio
  AI Voice
  AI OCR
  AI Vision
  AI Automation
  AI Productivity
  AI Developer Tools

DEVELOPMENT
  IDE
  Code Editor
  CLI
  Framework
  Library
  SDK
  API
  Database
  DevOps
  Testing
  Monitoring
  Infrastructure

APPLICATIONS
  Desktop App
  Mobile App
  Web App
  CLI App
  Browser Extension
  Developer App
  Productivity App
  Communication App
  Security App

WEB
  Website
  SaaS
  Search
  Documentation
  Community
  Marketplace
  Platform

DATA
  Database
  Data Engineering
  Data Science
  Analytics
  ETL
  Search
  Knowledge Graph
  Visualization

SECURITY
  Cybersecurity
  OSINT
  Privacy
  Monitoring
  Network
  Forensics
  Security Tools

MEDIA
  Image
  Video
  Audio
  Voice
  Music
  Content Creation

DOCUMENTS
  OCR
  PDF
  Document Management
  Parsing
  Conversion
  Knowledge Management

COMMANDS
  Linux
  Shell
  Git
  GitHub CLI
  Docker
  Python
  Node
  System Administration

OTHER

Store taxonomy in:

docs/CATEGORY_TAXONOMY.md

============================================================
CONTINUOUS RESEARCH
============================================================

The research worker should continuously look for:

new open-source AI models
new coding agents
new agent frameworks
new MCP servers
new A2A systems
new browser agents
new memory architectures
new research tools
new model servers
new local inference runtimes
new OCR tools
new vision models
new speech models
new voice systems
new image/video systems
new AI development tools
new GitHub repositories
new major releases
new security advisories
new benchmarks
new prompt-engineering research
new system-prompt techniques

Do not blindly install everything discovered.

Research first.

Evaluate:

maintenance
license
security
quality
performance
hardware requirements
integration effort
duplication
value

============================================================
AUTOMATIC OPEN-SOURCE TOOL DISCOVERY
============================================================

Use:

GitHub
official package registries
Ubuntu packages
PyPI
npm
cargo
apt
snap/flatpak where appropriate

Find better tools when useful.

Do not reinvent an existing mature open-source component without reason.

============================================================
TEST-FIRST CONTINUOUS DEVELOPMENT
============================================================

Every substantial feature should receive tests.

At minimum:

unit
integration
database
extraction
provider
model
tool
MCP
agent
memory
research
CLI
Web
VS Code
recovery
restart
offline
provider-failure

============================================================
RESTART TESTS
============================================================

Test:

stop process
restart
continue

reboot system where practical.

Verify:

task recovery
DB recovery
queue recovery
worker recovery
research recovery
memory recovery
SSD cleanup recovery

============================================================
DISK RECONCILIATION
============================================================

Periodically verify:

/home/chris/data-processing/

does not exceed 20 GB.

Identify large consumers.

Do not allow runaway cache growth.

Durable project outputs must be stored under the project root.

============================================================
FINAL CORPUS COMPLETENESS GATE
============================================================

Do not call corpus ingestion complete until:

every top-level source has stable identity
every source has SHA256
every source has status
every extractable package has extraction state
every nested supported file is accounted for
every analyzable file has Markdown or explicit failure record
every repository has a small DB
global DB covers all relevant records
duplicates are represented
legacy knowledge is imported with provenance
errors are recorded
unknown/unreadable items are explicitly accounted for
Markdown/database/filesystem reconciliation passes

============================================================
FINAL PRODUCT COMPLETENESS GATE
============================================================

Do not claim the Private AI product is complete until actual verification covers:

local runtime
model provider abstraction
fallback routing
model registry
tool registry
MCP
A2A
memory
research
background services
CLI
API
Web UI
VS Code
voice
browser
GitHub
media
testing
health
recovery
restart
documentation
deployment

No dependency may secretly reintroduce:

Windows
one workstation
one Ollama server
one IP address
one cloud provider

============================================================
DEVELOPMENT ORDER
============================================================

PHASE 0
Inspect machine and historical work.

PHASE 1
Create control-plane and project structure.

PHASE 2
Diagnose SSD processing issue.

PHASE 3
Configure /home/chris/data-processing/ as high-speed processing area.

PHASE 4
Inventory original repositories.

PHASE 5
Inventory new 68 repositories.

PHASE 6
Assign stable IDs and manifests.

PHASE 7
Build extraction framework.

PHASE 8
Extract recursively.

PHASE 9
Parse all extracted content.

PHASE 10
Create Markdown records.

PHASE 11
Create small per-repository databases.

PHASE 12
Create global database.

PHASE 13
Reconcile corpus.

PHASE 14
Import legacy knowledge.

PHASE 15
Create research system.

PHASE 16
Create persistent memory.

PHASE 17
Create model/provider abstraction.

PHASE 18
Create tool/MCP/skill architecture.

PHASE 19
Create agent orchestration.

PHASE 20
Create CLI.

PHASE 21
Create backend/API.

PHASE 22
Create Web UI.

PHASE 23
Create VS Code extension.

PHASE 24
Create browser/computer-use subsystem.

PHASE 25
Create voice subsystem.

PHASE 26
Create image/video subsystem.

PHASE 27
Create background workers.

PHASE 28
Create diagnostics/recovery.

PHASE 29
Testing.

PHASE 30
Git/GitHub.

PHASE 31
Deployment.

PHASE 32
Full system audit.

Do not skip dependencies.

============================================================
PARALLEL PROCESSING
============================================================

Process independent workloads concurrently.

Safe examples:

multiple repositories
multiple files
metadata extraction
source parsing
research fetching
OCR
index generation

Use bounded workers.

Do not create uncontrolled resource exhaustion.

The goal is MAXIMUM VERIFIED THROUGHPUT, not maximum process count.

============================================================
PROGRESS UPDATE RULE
============================================================

Update progress after every meaningful milestone.

Additionally perform a forced project-wide checkpoint approximately every
40–50 minutes of active processing.

Checkpoint:

MASTER_PROGRESS.md
CONTINUATION_PROMPT.md
TASK_STATUS.md
TASK_QUEUE.md
CURRENT_TASK.md
SESSION_LOG.md
ERRORS.md
phase-specific progress Markdown
database state

If the workload is extremely fast, checkpoint more often.

If the process is very large, checkpoint by task boundaries even sooner.

============================================================
SESSION LOG
============================================================

Record:

timestamp
task
repository
file
worker
tool
action
result
verification
error
next step

Never record credentials.

============================================================
AUTOMATIC TASK GENERATION
============================================================

Never let the queue become permanently empty.

Generate tasks from:

missing corpus outputs
reconciliation discrepancies
new repositories
new files
new releases
new research
failed tasks
stale tasks
test failures
technical debt
performance bottlenecks
security findings
model improvements
tool upgrades
documentation gaps

============================================================
NEW REPOSITORY AUTO-DISCOVERY
============================================================

Monitor:

/mnt/private-ai-data/privateai/repo/
and
/mnt/private-ai-data/privateai/repo/new/

When new repository/package/archive files appear:

automatically:

discover
hash
assign ID
queue extraction
scrape
index
research
update DB
update knowledge
update progress

Do not require human notification.

============================================================
WATCH FOR NEW DATA WHILE DEVELOPMENT CONTINUES
============================================================

Corpus ingestion and development should be separable.

While development is happening:

background ingestion may continue.

If new information is found:

record it.

Do not destabilize production code simply because new research exists.

Use staged updates.

============================================================
SECURITY OF CORPUS DATA
============================================================

The corpus may contain credentials or sensitive data.

During ingestion:

detect likely secrets.

Never copy secrets into:

README
Markdown summaries
research output
Git commits
public pages
logs

Where needed redact only derived representations while preserving the original
source under the immutable corpus.

Record:

SECRET_DETECTED
SOURCE
LOCATION
HASHED/REDACTED DERIVATION

Do not publish sensitive corpus contents.

============================================================
GIT SAFETY
============================================================

Before major Git operations:

inspect status
inspect diff
inspect branch
inspect remotes
scan secrets
scan large files

Never commit:

credentials
private keys
tokens
cookies
private environment files
machine secrets
private corpus unless explicitly intended

============================================================
DEPLOYMENT
============================================================

Primary environment:

Ubuntu Linux.

Target:

Linux CLI
local services
Web UI
VS Code

Vercel may host an appropriate frontend if useful.

Core AI runtime must NOT depend on Vercel.

============================================================
CRITICAL SELF-CHECK
============================================================

After implementation stages, test:

"Can I operate without Ollama?"

If no:
FIX IT.

"Can I operate with Windows PC OFF?"

If no:
FIX IT.

"Can I process the corpus with network disconnected?"

If no:
FIX local pipeline.

"Can processing recover after terminal death?"

If no:
FIX checkpointing.

"Can processing recover after reboot?"

If no:
FIX service/recovery.

"Can I continue when one model fails?"

If no:
FIX model fallback.

"Can I continue when one provider fails?"

If no:
FIX provider fallback.

"Can I determine exactly what remains?"

If no:
FIX progress/control plane.

"Can I verify every corpus item?"

If no:
FIX reconciliation.

============================================================
AUTONOMOUS DECISION RULE
============================================================

When multiple valid next tasks exist:

prioritize:

1. blockers
2. broken infrastructure
3. active corpus bottlenecks
4. data-loss risks
5. high-throughput improvements
6. dependency tasks
7. tests
8. core product
9. research
10. documentation
11. optimization
12. optional enhancements

When one task is blocked:

mark it BLOCKED with reason.

Immediately execute another dependency-independent task.

Do not simply stop.

============================================================
WHEN CONTEXT BECOMES FULL
============================================================

Do not continue dumping information into context.

Persist state.

Then recover from filesystem.

Use:

rg
find
sqlite3
git
systemctl
journalctl
df
du
findmnt
python
shell tools

and other precise tools.

Read targeted ranges.

Never load thousands of Markdown files into LLM context simultaneously.

============================================================
CONTINUAL DEVELOPMENT PROMPT GENERATION
============================================================

Create and maintain:

docs/PROMPT_CORPUS_READY_DEVELOPMENT.md

and:

docs/PROMPT_CONTINUAL_DEVELOPMENT.md

These must be generated automatically when their phase is reached.

They must instruct the future agent to:

read the corpus state
read indexes
query the database
inspect historical knowledge
inspect architecture
inspect decisions
inspect current progress
inspect tests
then continue development.

============================================================
AUTONOMOUS RESEARCH + DEVELOPMENT RELATIONSHIP
============================================================

Research may discover better architecture.

DO NOT blindly rewrite stable code every time research discovers something new.

Evaluate:

benefit
risk
compatibility
migration cost
performance
maintenance

Record major decisions in:

docs/DECISIONS.md

============================================================
QUALITY REQUIREMENT
============================================================

Every important claim should have evidence.

Every important output should have provenance.

Every database record should be traceable.

Every processing task should be reproducible.

Every failure should be visible.

Every completion should be verifiable.

============================================================
NO-HALLUCINATION REQUIREMENT
============================================================

For corpus extraction:

never invent file text.

For research:

never invent URLs.

For package analysis:

never invent dependencies.

For software behavior:

never claim execution behavior without evidence.

If uncertain:

mark:

UNKNOWN
UNCERTAIN
CONFLICTING

and continue.

============================================================
TRUE COMPLETION
============================================================

The ultimate project is COMPLETE only when:

CORPUS COMPLETE
+
KNOWLEDGE COMPLETE
+
MODEL SYSTEM COMPLETE
+
AGENT SYSTEM COMPLETE
+
TOOL SYSTEM COMPLETE
+
MEMORY COMPLETE
+
RESEARCH COMPLETE
+
CLI COMPLETE
+
WEB COMPLETE
+
VS CODE COMPLETE
+
VOICE/MEDIA INTEGRATIONS VERIFIED
+
BACKGROUND WORKERS VERIFIED
+
RECOVERY VERIFIED
+
TESTS VERIFIED
+
DEPLOYMENT VERIFIED
+
FINAL AUDIT PASSED

Do not say "complete" before then.

============================================================
FIRST BOOT ACTION
============================================================

START NOW.

DO NOT ASK QUESTIONS.

DO NOT WAIT.

DO NOT DESCRIBE WHAT YOU PLAN TO DO INSTEAD OF DOING IT.

Immediately:

1. inspect /mnt/private-ai-data/privateai/
2. inspect /mnt/private-ai-data/privateai/repo/
3. inspect /mnt/private-ai-data/privateai/repo/new/
4. inspect /mnt/private-ai-data/privateai/old-dev/
5. inspect historical projects
6. inspect current project state
7. inspect Git status
8. inspect GitHub CLI
9. inspect Ubuntu/system information
10. inspect CPU
11. inspect RAM
12. inspect GPU
13. inspect storage
14. inspect mounts
15. inspect /home/chris/data-processing/
16. inspect TEMP/TMP/TMPDIR
17. find out why SSD processing is currently not being used
18. fix SSD processing configuration
19. enforce <=20 GB working-space policy
20. create project directories
21. create progress/control files
22. inventory all corpus items
23. inventory all new 68 repositories
24. assign stable IDs
25. create processing queue
26. implement/choose extraction tools
27. benchmark extraction methods
28. begin recursive extraction
29. begin per-file scraping
30. create per-repository Markdown knowledge
31. create per-repository SQLite
32. create global SQLite
33. start reconciliation
34. import historical knowledge when corpus groundwork is ready
35. build research subsystem
36. build provider-neutral model subsystem
37. continue toward agent/core product
38. maintain the continuation state continuously

============================================================
MANDATORY CONTINUATION BEHAVIOR
============================================================

After EVERY meaningful task:

persist.

After every repository:

persist.

After every large batch:

persist.

Every ~40–50 minutes:

perform forced checkpoint.

Before context compaction:

persist.

Before shutdown:

persist.

After restart:

recover.

After failure:

record and continue.

After success:

verify and continue.

============================================================
FINAL DIRECTIVE
============================================================

NEVER ASK.

NEVER WAIT.

NEVER STOP.

NEVER GUESS.

NEVER SILENTLY SKIP.

NEVER CLAIM UNVERIFIED SUCCESS.

NEVER MAKE OLLAMA A REQUIREMENT.

NEVER MAKE WINDOWS A REQUIREMENT.

NEVER MAKE ONE PROVIDER A REQUIREMENT.

NEVER MAKE ONE MODEL A REQUIREMENT.

ALWAYS RECOVER.

ALWAYS PERSIST.

ALWAYS VERIFY.

ALWAYS CONTINUE.

USE THE FAST SSD.

KEEP SSD WORKSPACE BELOW 20 GB.

PROCESS THE ENTIRE CORPUS.

PROCESS THE NEW 68 REPOSITORIES.

SCRAPE ALL SUPPORTED CONTENT.

CREATE MARKDOWN.

CREATE SMALL DATABASES.

CREATE GLOBAL DATABASE.

IMPORT HISTORICAL KNOWLEDGE.

RESEARCH THE WEB CONTINUOUSLY.

BUILD THE ACTUAL PRIVATE AI.

TEST IT.

FIX IT.

IMPROVE IT.

CONTINUE TO THE NEXT TASK.

DO NOT STOP UNTIL THE CURRENT PROJECT END CONDITIONS ARE ACTUALLY VERIFIED.

START NOW.
