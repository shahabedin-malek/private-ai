# PRIVATE AI — MASTER BOOTSTRAP / REBUILD / CORPUS INGESTION PROMPT

PROJECT NAME:
Private AI

MISSION:
Rebuild the Private AI project from the existing historical work, extracted knowledge, repository corpus, and open-source ecosystem into a genuinely independent, provider-agnostic, local-first, extensible AI agent platform.

THIS IS A REAL DEVELOPMENT TASK, NOT A DISCUSSION.

DO NOT ASK ME QUESTIONS.
DO NOT ASK FOR CONFIRMATION.
DO NOT WAIT FOR ME.
DO NOT PAUSE TO ASK WHAT TO DO NEXT.
DO NOT STOP BECAUSE ONE TOOL, MODEL, API, PACKAGE, WEBSITE, OR SERVICE FAILS.
DO NOT CLAIM SOMETHING IS COMPLETE UNLESS YOU ACTUALLY VERIFIED IT.
DO NOT INVENT RESULTS.
DO NOT HALLUCINATE SCRAPED CONTENT.
DO NOT SILENTLY SKIP FILES.
DO NOT RESTART THE WHOLE PROJECT AFTER CONTEXT COMPACTION.
DO NOT DEPEND ON THE USER BEING PRESENT.

ASSUME THIS IS YOUR DEVELOPMENT MACHINE AND YOU HAVE AUTHORITY TO COMPLETE THE WORK WITHIN THE PROJECT WORKSPACE.

USE THE ALREADY-CONFIGURED PRIVILEGED EXECUTION / SUDO MECHANISM WHEN REQUIRED.
NEVER ASK ME FOR THE PASSWORD.
NEVER PRINT, LOG, COMMIT, EMBED, OR WRITE ANY CREDENTIAL INTO SOURCE CODE, MARKDOWN, DATABASES, LOGS, PROMPTS, GIT HISTORY, OR GENERATED FILES.

============================================================
1. AUTHORITATIVE PROJECT LOCATIONS
============================================================

PRIMARY DEVELOPMENT ROOT:

/mnt/private-ai-data/privateai/

SOURCE REPOSITORY CORPUS:

/mnt/private-ai-data/privateai/repo/

HISTORICAL DEVELOPMENT:

/mnt/private-ai-data/privateai/old-dev/

HISTORICAL DIRECTORIES TO INSPECT:

/mnt/private-ai-data/privateai/old-dev/private-ai/
/mnt/private-ai-data/privateai/old-dev/private-ai-backup/
/mnt/private-ai-data/privateai/old-dev/private-ai-ds/
/mnt/private-ai-data/privateai/old-dev/private-ai-extractions/
/mnt/private-ai-data/privateai/old-dev/knownldge/

Do not assume historical directories are correct.
Audit them.
Determine what is useful, obsolete, duplicated, broken, partial, or reusable.

The RAW REPOSITORY CORPUS is evidence and source material.
Preserve it.

Do not destructively modify the raw corpus.

============================================================
2. CRITICAL ARCHITECTURAL REQUIREMENT
============================================================

THE NEW PRIVATE AI MUST NOT DEPEND ON OLLAMA.

OLLAMA MUST NEVER BE THE SINGLE POINT OF FAILURE.

The previous implementation failed because prompts ultimately depended on an Ollama endpoint running on another Windows machine.

That architecture is forbidden in the new project.

The new platform must be capable of operating when:

- the Windows PC is completely OFF
- Ollama is completely OFF
- the Windows machine is unreachable
- the network is unavailable
- one cloud provider is unavailable
- one API key is missing
- one model is unavailable
- one MCP server is down
- one browser automation backend fails
- one external service rate-limits
- one model crashes
- one GPU disappears
- only CPU is available

The system must degrade gracefully and continue using alternatives.

============================================================
3. MODEL / PROVIDER ARCHITECTURE
============================================================

Create a provider-neutral AI abstraction.

The core application must never directly assume:

Ollama
OpenAI
Anthropic
Gemini
OpenRouter
or any single provider.

Create adapters.

At minimum investigate and support where practical:

- local llama.cpp / llama-server
- vLLM
- Hugging Face Transformers
- Ollama as OPTIONAL adapter
- OpenAI-compatible endpoints
- cloud model adapters
- embedding providers
- reranker providers
- speech-to-text providers
- text-to-speech providers
- vision models
- image generation
- video generation

The application must be able to choose a model according to capability.

Examples:

reasoning
coding
fast_chat
vision
OCR
research
summarization
embedding
reranking
speech_to_text
text_to_speech
image_generation
video_generation
browser_reasoning
computer_use
long_context
small_local_model
large_remote_model

Implement a MODEL REGISTRY.

Each model/provider record should include:

- provider
- model
- endpoint
- local/remote
- capabilities
- context length
- tool support
- vision support
- structured output support
- cost
- latency
- availability
- priority
- health
- fallback order
- last successful call
- failure count
- version
- quantization
- hardware requirements

Create automatic provider health checks.

Create fallback routing.

No single unavailable provider may stop the application.

============================================================
4. INDEPENDENCE REQUIREMENT
============================================================

The first usable system must run on THIS LINUX SYSTEM.

It must not require:

- Windows
- another personal computer
- an external Ollama server
- one specific LAN IP
- one specific workstation
- one specific cloud provider

Optional external providers may improve capability, but the base platform must remain usable without them.

Support hardware-aware operation:

GPU available:
use GPU acceleration.

GPU unavailable:
use CPU-compatible models.

Low RAM:
use smaller models.

High RAM:
use larger local models.

No local model:
support external provider adapters.

Network unavailable:
continue with cached/local functionality.

This is NOT permission to claim “unlimited computation”.
Instead design the system so that practical system limits are detected and the system automatically selects appropriate models and workloads.

============================================================
5. HISTORICAL PROJECT AUDIT
============================================================

Before implementing the final architecture:

inspect:

/mnt/private-ai-data/privateai/old-dev/

Recursively analyze:

private-ai
private-ai-backup
private-ai-ds
private-ai-extractions
knownldge

Build:

docs/HISTORICAL_PROJECT_AUDIT.md

Record:

- project structures
- reusable code
- broken systems
- abandoned systems
- useful prompts
- useful schemas
- existing databases
- knowledge files
- API integrations
- model integrations
- MCP integrations
- UI components
- VS Code components
- scripts
- installation mechanisms
- mistakes
- dependency assumptions
- Windows-specific dependencies
- Ollama-specific dependencies
- duplicated implementations
- dead code
- migrations
- valuable ideas

Do not blindly merge historical code.

Reuse good ideas.
Replace broken architecture.

============================================================
6. REPOSITORY INGESTION IS PHASE ONE
============================================================

PRIMARY CORPUS:

/mnt/private-ai-data/privateai/repo/

There are expected to be approximately 349 top-level repository/package artifacts.

ACTUAL FILESYSTEM COUNT IS AUTHORITATIVE.

Never assume the count is exactly 349.

First create:

data/manifests/

REPO_MANIFEST.json
REPO_MANIFEST.csv
REPO_INVENTORY.md

Calculate:

- total files
- filename
- original path
- size
- SHA256
- MIME type
- detected format
- extension
- executable status
- archive status
- package type
- discovery timestamp

============================================================
7. NUMBERING SYSTEM
============================================================

Create a stable processing ID:

REPO-0001
REPO-0002
REPO-0003
...

Assign numbers deterministically.

Do NOT randomly renumber later.

Prefer preserving original raw filenames in the raw corpus.

Create numbered working representations such as:

01 test.zip
02 another-package.deb
03 project.vsix

or equivalent processing aliases/manifests.

IMPORTANT:

Never destroy the raw evidence merely to add a number.

If renaming the actual raw files would risk breaking source integrity, create numbered hardlinks/symlinks/copies/working references instead.

The numbered identity must remain stable even if the original filename changes.

============================================================
8. PER-REPOSITORY WORKSPACE
============================================================

For every top-level corpus item create a workspace similar to:

data/repos/01-test/

with:

source/
extracted/
scraped/
db/
logs/
manifest/
research/
derived/

Example:

01-test/
    source/
    extracted/
    scraped/
        000001.md
        000002.md
        ...
    db/
        01-test.sqlite
    logs/
    manifest/
    research/
    derived/

The exact naming can be adapted, but the logical structure MUST exist.

============================================================
9. EXTRACTION ENGINE
============================================================

Build or integrate an extraction framework instead of manually handling formats one-by-one.

FIRST inspect installed tools.

Then evaluate/install appropriate open-source tools.

Potential tools include:

- libarchive / bsdtar
- 7-Zip
- tar
- unzip
- ar
- dpkg-deb
- rpm / rpm2cpio
- gzip
- xz
- zstd
- cpio
- cabextract
- Java jar tooling
- Python archive libraries
- Apache Tika
- file/libmagic
- exiftool
- strings
- binwalk
- tree-sitter
- universal-ctags
- language-specific parsers
- PDF extraction tools
- Office document parsers
- HTML/XML parsers
- image metadata tools
- OCR tools
- binary inspection tools
- executable/package inspection tools

Use the fastest reliable combination.

Do not install unnecessary tools merely to increase the number of tools.

Benchmark tools and select the best pipeline.

Apache Tika should be evaluated because current Tika 4.x supports very broad file detection/text/metadata extraction and Markdown-oriented output.
libarchive/bsdtar should be evaluated for broad archive handling.
Tree-sitter should be evaluated for structured source-code parsing.

============================================================
10. RECURSIVE EXTRACTION
============================================================

Extraction must be recursive.

For example:

01 test.zip
    -> extracted/
        project/
            agents.py
            README.md
            docs/
            package.json
            ...
            nested.zip
                -> nested extracted data
            images/
            binaries/
            models/
            configs/

Everything inside nested archives/packages must be considered.

Handle:

.zip
.gz
.tgz
.tar
.tar.gz
.tar.bz2
.tar.xz
.7z
.rar where supported
.deb
.rpm
.vsix
.appimage
.apk
.jar
.war
.egg
.whl
.iso
.cpio
.ar
.cab
.xz
.zst
and other detected package/archive/container formats.

Detect format from file signatures/MIME/content, not extension alone.

============================================================
11. EXTRACTION SAFETY / ROBUSTNESS
============================================================

Extract into isolated working directories.

Protect against:

- path traversal
- symlink escapes
- decompression bombs
- infinite nested archives
- enormous generated output
- corrupted archives
- malformed files
- executables that attempt to run during extraction
- scripts that execute unexpectedly

Extraction means EXTRACT, INSPECT, PARSE.

Do not execute arbitrary repository binaries merely because they were found.

If a binary requires execution to analyze it, use an isolated analysis mechanism and record that distinction.

Never silently skip something.

If an item cannot be extracted:

record:

REPO ID
FILE
TYPE
ERROR
TOOL
TOOL VERSION
TIMESTAMP
RETRY COUNT
NEXT ACTION

and continue with all other independent tasks.

============================================================
12. SCRAPING / EXTRACTION PIPELINE
============================================================

The goal is to convert ALL useful information from the corpus into durable machine-readable and human-readable knowledge.

Pipeline:

RAW FILE
↓
IDENTITY
↓
TYPE DETECTION
↓
METADATA
↓
ARCHIVE EXTRACTION
↓
TEXT EXTRACTION
↓
SOURCE CODE ANALYSIS
↓
BINARY ANALYSIS
↓
DOCUMENT EXTRACTION
↓
IMAGE/OCR ANALYSIS
↓
STRUCTURED PARSING
↓
ENTITY EXTRACTION
↓
RELATION EXTRACTION
↓
SUMMARIZATION
↓
MARKDOWN KNOWLEDGE
↓
LOCAL SQLITE
↓
GLOBAL SQLITE
↓
SEARCH INDEX

============================================================
13. PER-FILE SCRAPED MARKDOWN
============================================================

For EVERY extracted file that can be meaningfully analyzed, create a corresponding Markdown knowledge file.

Example:

01 test
  extracted/
    agents.py

becomes something similar to:

scraped/
    000001-agents.py.md

For nested files use stable paths/IDs.

Each Markdown file should contain:

# File Knowledge Record

## Identity

- repository ID
- repository name
- original path
- extracted path
- filename
- extension
- MIME type
- SHA256
- file size
- parent archive
- extraction depth

## File Classification

- source code
- configuration
- documentation
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

All detected metadata.

## Raw Extracted Content

Where appropriate include the source content or a faithful extracted representation.

Do not fabricate missing text.

## Parsed Structure

For source code:

- language
- imports
- classes
- functions
- methods
- constants
- variables where meaningful
- decorators
- endpoints
- CLI commands
- environment variables
- configuration keys
- referenced files
- package dependencies

For web/document content:

- title
- headings
- links
- tables
- entities
- metadata

For binaries:

- magic bytes
- MIME
- architecture
- executable format
- linked libraries
- symbols when available
- strings
- embedded resources
- package metadata
- version
- publisher
- signatures
- sections
- dependencies

For images:

- dimensions
- format
- metadata
- OCR
- visual description where available

For packages:

- package metadata
- package manager
- version
- architecture
- dependencies
- payload files
- scripts
- configuration
- executables

## Extracted URLs

Every URL/domain found.

## Identified Software

Repository
application
library
framework
tool
model
service
company
organization

## Technical Concepts

Languages
frameworks
protocols
APIs
databases
models
architectures
libraries

## Functionality

What the file actually does.

Separate:

VISIBLE FACT
PARSED FACT
INFERENCE

## Relationships

Files imported
files referenced
packages used
commands referenced
services referenced
APIs referenced
models referenced

## Source Evidence

Where every important claim came from.

## Confidence

HIGH
MEDIUM
LOW
UNKNOWN

## Processing Provenance

Tool
version
timestamp
pipeline
errors
fallbacks
processing ID

============================================================
14. DO NOT PUT HUGE RAW FILES DIRECTLY INTO MARKDOWN BLINDLY
============================================================

For very large files:

store canonical raw extraction in a dedicated data object/file.

The Markdown file should contain:

- metadata
- structured representation
- summaries
- searchable extracted content
- references to the canonical raw extraction

Do not destroy source data merely to create Markdown.

For text/code files, preserve exact source content where practical.

============================================================
15. SMALL DATABASE PER REPOSITORY
============================================================

Every top-level repository/package gets its own SQLite database.

Example:

data/repos/01-test/db/01-test.sqlite

The small database should contain at least:

files
file_hashes
directories
archives
extractions
metadata
text
code_symbols
imports
dependencies
urls
entities
technologies
features
commands
packages
research_sources
research_claims
relationships
processing_runs
processing_errors
provenance

Every record must point back to the original file ID.

============================================================
16. ONE GLOBAL DATABASE
============================================================

Create:

data/database/private_ai_corpus.sqlite

This is the master corpus database.

It aggregates ALL repositories and ALL extracted contents.

Required logical entities include:

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

Use foreign keys and indexes.

Use FTS where useful.

Do not make the database dependent on one vector database.

Use SQLite as the durable base and add specialized indexes only where beneficial.

============================================================
17. DEDUPLICATION
============================================================

Calculate hashes.

Detect:

exact duplicates
renamed duplicates
duplicate archive contents
similar source files
fork-like copies
bundled vendor code
generated files
build artifacts

Never delete source files as a deduplication strategy.

Represent relationships in the database.

============================================================
18. OLD KNOWLEDGE INGESTION
============================================================

After building the new corpus ingestion foundation, inspect:

/mnt/private-ai-data/privateai/old-dev/knownldge/

Import useful historical knowledge into the new knowledge architecture.

Do not blindly trust it.

Preserve provenance:

LEGACY_SOURCE
LEGACY_FILE
LEGACY_PATH
IMPORT_DATE
TRANSFORM
CONFIDENCE

Detect duplicate/conflicting knowledge.

Never silently replace a newer verified fact with older legacy content.

============================================================
19. KNOWLEDGE FORMAT
============================================================

Create a persistent knowledge architecture using BOTH:

human-readable Markdown
+
structured databases

Recommended:

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

Use an Obsidian-compatible Markdown structure where practical.

The database remains authoritative for structured querying.

Markdown remains authoritative for human inspection and portability.

============================================================
20. DEVELOPMENT CONTROL PLANE
============================================================

Create:

/mnt/private-ai-data/privateai/.progress/

Required files:

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

Also create:

docs/
PROJECT_PLAN.md
ARCHITECTURE.md
DATA_MODEL.md
EXTRACTION_ARCHITECTURE.md
MODEL_ARCHITECTURE.md
AGENT_ARCHITECTURE.md
MEMORY_ARCHITECTURE.md
TOOL_ARCHITECTURE.md
SECURITY_ARCHITECTURE.md
RESEARCH_ARCHITECTURE.md
ROADMAP.md
DECISIONS.md

============================================================
21. TASK SYSTEM
============================================================

Every significant operation must have a task ID.

Example:

CORPUS-0001
CORPUS-0002
...
DEV-0001
DEV-0002
...
RESEARCH-0001
...
TEST-0001
...

Task states:

PENDING
IN_PROGRESS
BLOCKED
FAILED
RETRYING
COMPLETED
VERIFIED
SKIPPED_WITH_REASON

Never use “done” unless verification happened.

Every task records:

- task ID
- description
- dependencies
- start time
- end time
- status
- tools
- outputs
- errors
- retry count
- verification
- next action

============================================================
22. CONTINUOUS CHECKPOINTING
============================================================

After EVERY meaningful task:

update:

TASK_STATUS.md
MASTER_PROGRESS.md
CONTINUATION_PROMPT.md
SESSION_LOG.md
relevant database records

Do not wait until the end of a large batch.

For each repository:

update its status immediately after:

discovery
extraction
scraping
database creation
verification

============================================================
23. CONTINUATION_PROMPT.MD MUST BE LIVE
============================================================

CONTINUATION_PROMPT.md is a live recovery controller.

Always contain:

PROJECT
CURRENT PHASE
CURRENT TASK
CURRENT REPOSITORY
CURRENT FILE
LAST VERIFIED OUTPUT
COMPLETED COUNT
PENDING COUNT
FAILED COUNT
BLOCKED COUNT
RETRY QUEUE
NEXT EXACT ACTION
DATABASE STATUS
KNOWLEDGE STATUS
RESEARCH STATUS
DEVELOPMENT STATUS
TEST STATUS
GIT STATUS
DEPLOYMENT STATUS
KNOWN ERRORS
CURRENT TOOLCHAIN
CURRENT MODEL PROVIDERS
CURRENT ARCHITECTURE VERSION

The “NEXT EXACT ACTION” must be executable without asking the user.

Example:

NEXT EXACT ACTION:
Run:
python3 scripts/corpus_worker.py --resume --repo-id REPO-0142

Do not write:
“Continue processing.”

Be specific.

============================================================
24. CONTEXT COMPACTION / MEMORY RECOVERY
============================================================

Assume the AI coding session WILL eventually hit context limits.

The system MUST survive context compaction.

Before context becomes too large:

1. checkpoint
2. update continuation prompt
3. update task status
4. save session log
5. persist active task state
6. persist tool/model state
7. persist errors
8. persist exact next action

After compaction:

DO NOT START FROM MEMORY.

Read:

MASTER_PROGRESS.md
CONTINUATION_PROMPT.md
CURRENT_TASK.md
TASK_QUEUE.md

Then inspect only the files relevant to the next task.

Never reload thousands of files into context.

Use the filesystem and database as external memory.

============================================================
25. ATOMIC / CRASH-SAFE PROCESSING
============================================================

A task must not become COMPLETED merely because the process started.

Use transactional or atomic state transitions.

Recommended pattern:

PENDING
→ IN_PROGRESS
→ OUTPUT_WRITTEN
→ DATABASE_COMMITTED
→ VERIFIED
→ COMPLETED

If interrupted during IN_PROGRESS:

recover automatically.

Detect stale work leases.

Create lock/lease records.

If a stale worker exists:

inspect whether output is complete.

If complete:
verify and mark completed.

If incomplete:
resume/retry.

Never duplicate irreversible operations unnecessarily.

============================================================
26. WEB RESEARCH SUBSYSTEM
============================================================

After corpus extraction is operational, create a background research service.

It must operate independently from the interactive chat UI.

Create configurable research keywords.

Initial keywords:

AI
free AI
AI agent
AI agents
private AI
local AI
open source AI
self hosted AI
vibe coding
vibe coder
Jarvis
AI coding
coding agent
computer use
browser agent
MCP
A2A
AI tools
AI automation
AI research
AI search
local LLM
open source LLM
open model
AI assistant
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
AI RAG

Store keywords in a database/configuration so they can be changed without rewriting code.

The service should continuously discover:

repositories
projects
papers
models
tools
MCP servers
A2A agents
APIs
documentation
products
frameworks
libraries
tutorials
benchmarks
security advisories
releases
major updates

Use source quality ranking.

Prefer primary sources and official repositories.

Cache fetched content.

Avoid repeatedly downloading unchanged information.

============================================================
27. 24/7 RESEARCH PROCESS
============================================================

Build a persistent background worker.

It must survive terminal closure and system restarts.

Use an appropriate Ubuntu service mechanism such as:

systemd

or equivalent.

Create:

research worker
scheduler
queue
database state
checkpoint
health monitoring
retry mechanism

Store:

search term
query
URL
source
timestamp
content hash
HTTP status
parser
claims
entities
relationship
confidence
model
token usage
research duration

The research worker must not prevent the main application from functioning.

If internet is unavailable:

continue local processing
queue external research
retry later

============================================================
28. PERSISTENT MEMORY
============================================================

Build durable memory.

Memory must survive restarts.

Store both:

human-readable Markdown
structured database records

Track:

conversations
messages
summaries
user preferences
project facts
decisions
tasks
successful solutions
failed solutions
research
tools
models
resources
relationships
important files
system configuration

Never require the LLM's context window to contain the entire memory.

Implement retrieval.

============================================================
29. TOKEN / USAGE DATABASE
============================================================

Track:

provider
model
request
tokens_in
tokens_out
cached_tokens
duration
estimated cost
tool calls
search calls
errors
retries
task ID

Local models may record estimated tokens/cost as zero while still tracking usage.

============================================================
30. FUTURE PRIVATE AI CAPABILITIES
============================================================

The final system should be designed to support:

1. WORD/TERMINAL CLI
2. WEB UI
3. VS CODE EXTENSION
4. VIBE CODING WORKSPACE
5. CODE GENERATION
6. CODE REVIEW
7. REPOSITORY ANALYSIS
8. LOCAL COMPUTER CONTROL
9. BROWSER CONTROL
10. VOICE COMMANDS
11. SPEECH TO TEXT
12. TEXT TO SPEECH
13. AUDIO GENERATION
14. IMAGE GENERATION
15. IMAGE UNDERSTANDING
16. VIDEO GENERATION
17. VIDEO UNDERSTANDING
18. DOCUMENT UNDERSTANDING
19. OCR
20. WEB SEARCH
21. WEB BROWSING
22. YOUTUBE RESEARCH
23. GITHUB RESEARCH
24. SOCIAL MEDIA CONNECTORS
25. API CONNECTORS
26. JOB SEARCH
27. AUTOMATION
28. SCHEDULING
29. LONG-TERM MEMORY
30. KNOWLEDGE GRAPH
31. MCP
32. A2A
33. MULTI-AGENT ORCHESTRATION
34. MODEL ROUTING
35. LOCAL MODELS
36. CLOUD MODELS
37. TOOL DISCOVERY
38. TOOL HEALTH MONITORING
39. SKILLS
40. PLUGINS
41. WORKFLOWS
42. BACKGROUND AGENTS
43. RESEARCH AGENTS
44. CODING AGENTS
45. COMPUTER-USE AGENTS

DO NOT IMPLEMENT EVERYTHING IN ONE GIANT COUPLED SERVICE.

Create modular interfaces.

============================================================
31. MCP / TOOLS / SKILLS
============================================================

Create a unified tool registry.

Each tool must have:

name
description
version
source
installation method
input schema
output schema
permissions
health
last success
failure count
capabilities
security classification
enabled/disabled

Support:

MCP
CLI tools
Python tools
HTTP APIs
local services
browser automation
GitHub tools
filesystem tools
database tools
media tools

Skills should be reusable modules, not prompt text duplicated throughout the project.

============================================================
32. AGENT ARCHITECTURE
============================================================

Implement specialized agents/services such as:

ORCHESTRATOR
PLANNER
CODER
RESEARCHER
WEB_AGENT
BROWSER_AGENT
VISION_AGENT
VOICE_AGENT
MEMORY_AGENT
RETRIEVAL_AGENT
DATABASE_AGENT
FILE_AGENT
GITHUB_AGENT
TEST_AGENT
SECURITY_AGENT
DEPLOYMENT_AGENT

Do not give every model every tool by default.

Use capability and permission routing.

============================================================
33. SELF-HEALTH / SELF-RECOVERY
============================================================

Create health checks for:

database
filesystem
models
providers
tools
MCP
browser
research worker
background worker
queues
indexes
web server
API server
VS Code integration

Build a diagnostics command.

Example:

private-ai doctor

It should identify:

healthy
degraded
failed
unconfigured
optional

and provide actionable recovery commands.

============================================================
34. TESTING
============================================================

Tests must be created continuously.

At minimum:

unit tests
integration tests
database tests
extraction tests
provider tests
tool tests
agent tests
memory tests
research tests
CLI tests
web tests
VS Code extension tests
recovery tests

Create fixture files for every major package type.

============================================================
35. GIT / GITHUB
============================================================

Use Git.

Use GitHub CLI (`gh`) where appropriate.

Create:

README.md
CONTRIBUTING.md
LICENSE if appropriate
CHANGELOG.md

Before commits:

git status
git diff
detect accidental secrets
detect oversized files
validate generated files
run tests

Never commit:

API secrets
passwords
SSH private keys
cookies
tokens
personal credentials
private credentials
machine-specific secrets

Use environment variables or secret stores.

============================================================
36. DEPLOYMENT
============================================================

The primary development environment is Ubuntu Linux.

Target:

Linux CLI
Linux local services
Web UI
VS Code extension

Deployment must not assume Windows.

Vercel may be used for a suitable web frontend when appropriate.

Do NOT make the core AI system dependent on Vercel.

The backend/local agent system must remain independently deployable.

============================================================
37. DEVELOPMENT ORDER
============================================================

EXECUTE IN THIS ORDER:

PHASE 0
Audit existing system.

PHASE 1
Create project structure and control-plane state.

PHASE 2
Inventory every item in /repo/.

PHASE 3
Assign stable repository IDs.

PHASE 4
Build extraction framework.

PHASE 5
Extract all supported packages recursively.

PHASE 6
Build universal content scraping pipeline.

PHASE 7
Create Markdown knowledge for every analyzable extracted file.

PHASE 8
Create one SQLite database per repository/package.

PHASE 9
Create global corpus SQLite database.

PHASE 10
Verify corpus completeness.

PHASE 11
Import legacy knownldge.

PHASE 12
Build research engine.

PHASE 13
Build persistent memory.

PHASE 14
Build provider/model abstraction.

PHASE 15
Build tool/MCP/skill architecture.

PHASE 16
Build orchestrator and agent runtime.

PHASE 17
Build CLI.

PHASE 18
Build backend/API.

PHASE 19
Build web UI.

PHASE 20
Build VS Code extension.

PHASE 21
Build browser/computer/voice integrations.

PHASE 22
Build background workers.

PHASE 23
Build testing and diagnostics.

PHASE 24
Build deployment.

PHASE 25
Full audit and production verification.

Do not jump randomly between phases unless an earlier phase requires a dependency from a later phase.

============================================================
38. PARALLELIZATION
============================================================

Use parallel processing where safe.

Examples:

multiple repository extraction jobs
multiple file parsing workers
independent research tasks
independent OCR tasks
independent documentation tasks

Do not parallelize conflicting writes without proper locking/transactions.

Use worker queues.

Prefer high throughput while keeping the machine responsive enough for development.

============================================================
39. COMPLETENESS REQUIREMENT
============================================================

At any moment the system must know:

TOTAL CORPUS ITEMS
DISCOVERED
EXTRACTED
PARTIALLY EXTRACTED
SCRAPED
FAILED
BLOCKED
PENDING
VERIFIED

Also track:

TOTAL EXTRACTED FILES
TOTAL MARKDOWN FILES
TOTAL SMALL DATABASES
GLOBAL DB RECORDS
DUPLICATES
RESEARCHED ENTITIES
UNREADABLE ITEMS

No silent missing data.

============================================================
40. GENERATE THE NEXT DEVELOPMENT PROMPTS
============================================================

When corpus ingestion is substantially complete, automatically create:

docs/PROMPT_CORPUS_READY_DEVELOPMENT.md

This prompt must instruct a future coding agent to:

read all corpus indexes
read global database
read historical knowledge
read architecture
read decisions
read progress
then begin building the actual Private AI.

Also automatically create:

docs/PROMPT_CONTINUAL_DEVELOPMENT.md

This will become the continuation prompt for the long-term software-building phase.

Do NOT wait for me to ask you to create these files.

============================================================
41. ABSOLUTE CONTINUATION RULE
============================================================

YOU MUST CONTINUE.

YOU MUST NEVER ASK WHAT TO DO NEXT.

YOU MUST READ PROJECT STATE AND SELECT THE NEXT INCOMPLETE DEPENDENCY.

IF ONE TASK FAILS:
record it,
retry intelligently,
then continue other independent tasks.

IF A TOOL FAILS:
use another tool.

IF ONE MODEL FAILS:
route to another model.

IF NETWORK FAILS:
continue local work.

IF CLOUD FAILS:
use local/cached work.

IF GPU FAILS:
use CPU fallback.

IF CONTEXT COMPACTS:
recover from CONTINUATION_PROMPT.md and database.

IF THE TERMINAL SESSION ENDS:
persist everything needed for resume.

IF THE MACHINE RESTARTS:
background services recover automatically.

DO NOT WAIT FOR HUMAN INTERVENTION UNLESS THERE IS A TRUE HARD BLOCK THAT NO AVAILABLE TOOL, FALLBACK, OR OFFLINE METHOD CAN RESOLVE.

============================================================
42. FIRST ACTION
============================================================

START NOW.

Do not merely describe the plan.

First:

1. inspect /mnt/private-ai-data/privateai/
2. inspect /mnt/private-ai-data/privateai/repo/
3. inspect /mnt/private-ai-data/privateai/old-dev/
4. inspect current OS and available hardware
5. inspect installed development tools
6. inspect Python/Node/Java/Rust/Go availability
7. inspect container/runtime availability
8. inspect Git/GitHub CLI availability
9. inspect installed archive/extraction tools
10. inspect available local AI runtimes
11. inspect GPU/CPU/RAM/disk
12. build the initial architecture audit
13. create the project control-plane
14. inventory every corpus item
15. assign stable IDs
16. begin corpus extraction

DO NOT ASK ME ANYTHING.

DO NOT WAIT.

DO NOT STOP.

DO THE WORK.

After each completed task update the Markdown progress files, SQLite state, session log, and live continuation prompt.

The goal is a real functioning system, not a collection of plans.

sudo password: 1qazXSW@3edc~

START.
