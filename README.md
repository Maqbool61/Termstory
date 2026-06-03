# TermStory — Private Developer Reference Manual

Welcome to **TermStory**, your personal developer memory engine. 

This repository parses your shell history (`zsh`/`bash`), groups commands into active work sessions, correlates Git commit messages, and formats them into a high-density, searchable work timeline. 

This document serves as your complete, detailed reference manual detailing the internal architecture, database schemas, privacy sanitizer pipeline, interactive terminal interface, AI configuration, CLI usage, and local setups.

---

## Table of Contents
1. [Core Philosophy](#1-core-philosophy)
2. [Project Layout & Directory Structure](#2-project-layout--directory-structure)
3. [Chronological Ingestion Pipeline](#3-chronological-ingestion-pipeline)
4. [Shell History Parsing Mechanics](#4-shell-history-parsing-mechanics)
5. [VCS Root Resolution & Project Name Humanization](#5-vcs-root-resolution--project-name-humanization)
6. [Git Commit Correlation Pipeline](#6-git-commit-correlation-pipeline)
7. [Database Internals & Schema Reference](#7-database-internals--schema-reference)
8. [Privacy Sanitizer Pipeline](#8-privacy-sanitizer-pipeline)
9. [Zero-Dependency LLM API Client](#9-zero-dependency-llm-api-client)
10. [Interactive TUI Dashboard Layout & Style System](#10-interactive-tui-dashboard-layout--style-system)
11. [AI Prompts & Narrative Design Rules](#11-ai-prompts--narrative-design-rules)
12. [CLI Command Reference](#12-cli-command-reference)
13. [Configuration Reference (`config.json`)](#13-configuration-reference-configjson)
14. [Developer Verification & Testing Suite](#14-developer-verification--testing-suite)
15. [Troubleshooting & Personal Customization Hacks](#15-troubleshooting--personal-customization-hacks)

---

## 1. Core Philosophy

TermStory is **not** an audit log, a monitoring tool, or a dry analytics reporter. It is a **developer memory engine** built around these core design tenets:

* **Recognize, don't inspect**: Designed to help you instantly recognize what you worked on ("Ah, that was when I fixed container networking on project X") rather than scrolling through a wall of raw `cd`, `ls`, or `git status` commands.
* **Density over decoration**: The terminal TUI and CLI outputs avoid bloated double borders, rounded corners, or massive empty margins. Spacing is tight, information is dense, and column alignments are clean.
* **Screenshot-friendly**: Every view in the TUI is designed to fit onto a standard terminal grid and tell a clear, self-contained story of a day, a month, or a project.
* **Noise reduction**: Filters out routine, repetitive, and context-free commands (`ls`, `cd`, `git status`, `clear`, etc.) while highlighting creative actions (`git commit`, `docker compose up`, schema migrations, unit test executions).
* **Project Disambiguation & Mapping**: Translates raw directory basenames (like `incubator-hugegraph`) into human-friendly names (`Apache HugeGraph`) and maps untracked workspaces or general commands to a unified `"Other"` category.

---

## 2. Project Layout & Directory Structure

Below is the directory map of the TermStory repository:

```
termstory/
├── setup.py                    # Packaging metadata and dependency registrations
├── requirements.txt            # Package list (rich, typer, textual, pytest, etc.)
├── agents.md                   # Memory engine active development state & context
├── DATA_PRIVACY.md             # High-level data handling policies for the LLM pipeline
├── README.md                   # This master reference document
├── termstory/                  # Source package directory
│   ├── __init__.py             # Module exports
│   ├── __main__.py             # CLI wrapper entry point (allows python3 -m termstory)
│   ├── cli.py                  # Typer CLI application: parses command arguments & formats outputs
│   ├── tui.py                  # Textual Terminal User Interface dashboard & modals
│   ├── parser.py               # Shell history file reading & cleaning engine
│   ├── session.py              # In-memory command sequencing & timeline sessionizer
│   ├── project.py              # Git/VCS root directory matching & project humanization
│   ├── git_integration.py      # Local subprocess client calling git log & cleaning commit logs
│   ├── database.py             # SQLite wrapper: manages schemas, queries, caching & WAL settings
│   ├── date_utils.py           # Timezones, timestamp conversions, and date calculations
│   ├── sanitizer.py            # Local credentials, token, IP & hostname redaction rules
│   ├── ai.py                   # Zero-dependency LLM interface client using urllib.request
│   ├── insights.py             # Calculations for Focus Scores, active times & stats
│   ├── models.py               # Dataclasses representing Session, Project, Command, and Commit
│   └── formatter.py            # Output layout logic, emoji matrices, and Rich styling utils
└── tests/                      # Testing package directory
    ├── fixtures/
    │   └── sample_history.txt  # Fake history stream for parser tests
    ├── test_parser.py          # Verifies shell history extraction
    ├── test_session.py         # Asserts session chunking thresholds
    ├── test_project.py         # Tests workspace parent root resolution
    ├── test_git_integration.py # Mock tests for git log processes
    ├── test_database.py        # SQLite transaction & connection checks
    ├── test_database_queries.py# Verifies date range filters & caches
    ├── test_sanitizer.py       # Validates redactions & blacklists
    ├── test_ai.py              # Verifies prompts & HTTP client mocks
    ├── test_tui.py             # Textual app lifecycle tests & modal simulations
    ├── test_formatter_rich.py  # Tests CLI layouts & styling
    ├── test_insights.py        # Asserts Focus Score arithmetic
    └── test_integration.py     # End-to-end flow checks
```

---

## 3. Chronological Ingestion Pipeline

Data moves through a multi-stage pipeline whenever you query a CLI command or open the TUI dashboard:

1. **Ingest History Files**:
   * Reads target shell history files (`~/.zsh_history`, `~/.bash_history`).
   * Normalizes timestamps, separates multiline command backslashes (`\`), and constructs a flat sequence of `Command` objects.
2. **Chunk Sessions**:
   * Walks the command sequence chronologically.
   * If the time gap between two commands exceeds **30 minutes**, a new session boundary is created.
3. **Map Projects**:
   * Looks up the file directory where the command was executed.
   * Scans upward to find the repository configuration root (`.git`, `.hg`, `.svn`).
   * Normalizes the directory name to a human-readable title. If no project is resolved, maps the session to the `"Other"` category.
4. **Ingest Git Commits**:
   * Runs local `git log` commands to collect commits pushed/committed within the active session boundaries.
   * Cleans emojis and tags from commit logs to prevent formatting bugs.
5. **Sanitize Data locally**:
   * Runs the credentials sanitizer.
   * Drops blacklisted commands from AI processing (short-circuiting them to return `"Security/Authentication Operations"`).
   * Redacts IPs, passwords, FQDNs, URLs, and secret environment variables.
6. **Save & Cache**:
   * Writes the resulting objects to `~/.termstory/termstory.db`.
   * Caches high-level Month and Date summary strings in `macro_summaries`.
7. **Render & Visualize**:
   * Outputs the results to standard stdout (formatted via `Rich` tables) or launches the non-blocking `Textual` TUI.

---

## 4. Shell History Parsing Mechanics

The parsing engine in [parser.py](file:///Users/himanshuverma/Projects/termstory/termstory/parser.py) handles differences between shell formatting styles:

### Zsh History Extended Format
Zsh records commands in the format:
```
: <timestamp>:<duration>;<command>
```
* **Regex Extraction**: `^:\s*(\d+):(\d+);(.*)$` isolates the timestamp, elapsed duration, and command text.
* **Multiline Support**: If a command ends with `\`, the parser continues appending lines until the backslash pattern is broken, ensuring complete code blocks (such as complex Docker configurations or make scripts) are captured.

### Bash History Format
Standard Bash histories only write raw command strings sequentially. If `HISTTIMEFORMAT` is configured, Bash writes timestamp headers beforehand:
```
#1620000000
git commit -m "docs"
```
* **Header Matching**: The parser checks for lines matching `^#(\d{10})$`.
* **Missing Timestamp Heuristics**: If timestamps are missing entirely, the parser calculates them using a **Backward-and-Forward Fill Algorithm**:
  1. Retrieve the file's last modified time (`mtime`) as a baseline reference.
  2. Map timestamps backwards in 10-second decrements from `mtime` for all trailing commands.
  3. If some lines have timestamp markers while others do not, the parser fills the gaps chronologically using linear 10-second increments between known points.

---

## 5. VCS Root Resolution & Project Name Humanization

To avoid naming logs after temporary folders, the resolver in [project.py](file:///Users/himanshuverma/Projects/termstory/termstory/project.py) uses a double-tiered identification strategy:

```
                 Working Directory (e.g. /home/dev/src/termstory/tests)
                                         ↓
                     Search upward for VCS Roots (.git, .hg, .svn)
                                         ↓
                   [Found Root] -> /home/dev/src/termstory
                                         ↓
           Check config files (package.json, setup.py, Cargo.toml, etc.)
                                         ↓
          [Found package.json name] -> "termstory-tui" -> Map to "TermStory"
```

### Disambiguation Maps
Common abbreviations and workspace folders are mapped to clean names:
* Empty or system-level actions (e.g. commands run in `~` or `/`) are mapped to `"Other"`.
* Name humanization rules clean up string casing, strip trailing hyphens, and convert system terms (e.g. mapping `infra-k8s` to `Infra K8s`).

---

## 6. Git Commit Correlation Pipeline

To map Git history to shell commands, the engine in [git_integration.py](file:///Users/himanshuverma/Projects/termstory/termstory/git_integration.py) performs these steps:

1. **Subprocess Calls**: Spawns a non-interactive shell command:
   ```bash
   git log --all --since="<session_start>" --until="<session_end>" --format="%H|%ct|%s"
   ```
2. **Conventional Commit Cleaning**:
   * Removes commit categorization prefixes (e.g. `feat(tui):` becomes `tui:`, `fix:` is stripped).
   * Strips git emojis (e.g. `:bug:`, `:fire:`, `🚀`).
   * Drops merge branch references and commits matching standard merge pull request messages.
3. **Commit Association**: Maps matching commits to the active session by checking if they fall within the session's duration window.

---

## 7. Database Internals & Schema Reference

The storage layer in [database.py](file:///Users/himanshuverma/Projects/termstory/termstory/database.py) uses SQLite.

### WAL Configuration
Upon initialization, the database sets Write-Ahead Logging (WAL) to prevent database locks when background threads query the LLM while the user interacts with the timeline:
```sql
PRAGMA journal_mode = WAL;
```

### Database Tables Schema

```sql
-- 1. Track workspaces
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    path TEXT,
    first_seen INTEGER,
    last_seen INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- 2. Sessions chronological groupings
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time INTEGER NOT NULL,
    end_time INTEGER NOT NULL,
    duration_seconds INTEGER,
    project_id INTEGER,
    ai_summary TEXT,  -- Cached session narrative
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 3. Individual command logs
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    command TEXT NOT NULL,
    exit_code INTEGER,
    session_id INTEGER,
    project_id INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(session_id) REFERENCES sessions(id),
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 4. Cleaned git commits
CREATE TABLE IF NOT EXISTS commits (
    hash TEXT PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    message TEXT NOT NULL,
    cleaned_message TEXT NOT NULL,
    project_id INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY(project_id) REFERENCES projects(id)
);

-- 5. Timeframe summaries cache (for TUI navigation speed)
CREATE TABLE IF NOT EXISTS macro_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timeframe_id TEXT NOT NULL UNIQUE, -- e.g. "2026-06-03" or "June 2026"
    type TEXT NOT NULL,                -- "date" or "month"
    summary TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);
```

---

## 8. Privacy Sanitizer Pipeline

The local sanitizer pipeline in [sanitizer.py](file:///Users/himanshuverma/Projects/termstory/termstory/sanitizer.py) ensures no sensitive tokens, credentials, or hostnames reach the LLM API.

### A. Blacklist Filters
If a command matches any of the following patterns, the entire session's AI request is aborted, and the database stores a fallback status message:
```python
BLACKLIST_PATTERNS = [
    re.compile(r'\bvault\b', re.IGNORECASE),
    re.compile(r'\baws\s+configure\b', re.IGNORECASE),
    re.compile(r'\bgh\s+auth\b', re.IGNORECASE),
    re.compile(r'\bkubectl\s+.*?\bcreate\s+secret\b', re.IGNORECASE)
]
```

### B. Regular Expression Masking Rules

| Parameter | Regex Match Rule | Replacement Target |
|---|---|---|
| **Private Keys** | `-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END...` | `[REDACTED_PRIVATE_KEY]` |
| **AWS API Keys** | `\b(?:AKIA\|ASIA)[A-Z0-9]{16}\b` | `[REDACTED_AWS_KEY]` |
| **Slack Tokens** | `\bxoxb-[0-9]{11,13}-[a-zA-Z0-9]{24}\b` | `[REDACTED_SLACK_TOKEN]` |
| **Bearer Tokens** | `\bbearer\s+([a-zA-Z0-9\-._~+/]+=*)\b` | `Bearer [REDACTED_TOKEN]` |
| **Exports** | `(export\s+[A-Za-z0-9_]+=)([^ ]+)` | `export KEY=[REDACTED]` |
| **Auth Flags** | `--password`, `-p`, `--token`, `--api-key` | `--password=[REDACTED]` |
| **IP Addresses** | `\b(?:\d{1,3}\.){3}\d{1,3}\b` | `[REDACTED_IP]` |

### C. FQDN Exclusions
The pipeline preserves file paths and configs by checking match extensions against a whitelist:
```python
FILE_EXTENSIONS = {
    'py', 'json', 'db', 'sh', 'xml', 'yml', 'yaml', 'md', 'txt', 'c', 'cpp',
    'h', 'go', 'java', 'js', 'ts', 'html', 'css', 'sqlite', 'sqlite3', 'rs'
}
```
If a matched string ends with an extension in this list (e.g. `config.json`), it is left untouched. Otherwise, hostnames are replaced with `[REDACTED_HOST]`.

---

## 9. Zero-Dependency LLM API Client

The communication module in [ai.py](file:///Users/himanshuverma/Projects/termstory/termstory/ai.py) connects to OpenAI-compatible endpoints using Python's native standard library:

* **Urllib Requester**: Employs `urllib.request.Request` to perform POST payloads, eliminating dependencies on libraries like `requests` or `openai-python`.
* **URL Normalization**: Normalizes base URL paths by stripping trailing slashes to prevent duplicate path slashes:
  ```python
  endpoint = api_base_url.strip().rstrip('/')
  if not endpoint.endswith('/chat/completions'):
      endpoint = f"{endpoint}/chat/completions"
  ```
* **Empty Key Check**: Local instances (like Ollama running on `localhost:11434`) do not require authentication. The client checks if the API key is empty and skips adding the `Authorization: Bearer` header:
  ```python
  if api_key and isinstance(api_key, str) and api_key.strip():
      headers["Authorization"] = f"Bearer {api_key.strip()}"
  ```

---

## 10. Interactive TUI Dashboard Layout & Style System

The interactive dashboard is powered by the `Textual` framework:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  StatsHeader (Streak Count, Active Days, Cumulative Duration, Command Heatmap)         │
├─────────────────────────────────────────┬──────────────────────────────────────────────┤
│  HistoryTree (Timeline Navigator)       │  DetailsCanvas (Main Panel)                  │
│  - June 2026                            │  - AI Timeframe summaries                    │
│    - Jun 03 (Wed)                       │  - Card breakdowns (Commits, Projects)       │
│      - TermStory                        │  - Time Distribution charts                  │
│        - session 09:15-09:45            │  - Git Commit lists                          │
│                                         │  - Command Timelines with noise muted)       │
└─────────────────────────────────────────┴──────────────────────────────────────────────┘
```

### CSS Layout Rules
The layout is defined in [tui.py](file:///Users/himanshuverma/Projects/termstory/termstory/tui.py):
* **Master Layout Grid**: Sets up a `2 x 2` grid:
  ```css
  #master-layout {
      layout: grid;
      grid-size: 2 2;
      grid-rows: 3 1fr;
      grid-columns: 30% 70%;
      height: 1fr;
      grid-gutter: 0;
  }
  ```
* **Stats Header**: Spans two columns (`column-span: 2`) at a fixed height of `3` rows, keeping a dark background (`#1a1a1e`) and a border separating it from the main workspace.
* **Explorer & Canvas Panels**: Set to scrollable height blocks with a dark background (`#121214`), separated by a thin vertical line (`border-right: solid #323238`).

### Navigation & Shortcuts Help Screen
Pressing `?` opens a centered modal help overlay containing keyboard shortcuts. It can be dismissed by pressing `Escape`, `q`, or clicking Close.

| Category | Key | Action |
|---|---|---|
| **Global Navigation** | `?` | Toggle Shortcuts Help Menu |
| | `/` | Open dynamic regex Search / Filter box |
| | `o` | Open AI Configuration Onboarding Screen |
| | `q` / `Esc` | Quit dashboard / Close active modal / Clear search filter |
| **Canvas Scrolling** | `Ctrl+Down` / `Ctrl+j` | Scroll details canvas down |
| | `Ctrl+Up` / `Ctrl+k` | Scroll details canvas up |
| | `Ctrl+PgDn` / `Ctrl+PgUp` | Scroll details canvas by half-page |
| **Timeline Explorer** | `j` / `k` (or arrows) | Navigate up and down the timeline tree nodes |
| | `Enter` / `Space` | Expand or collapse chronological tree groupings |
| **Onboarding Form** | `Ctrl+g` / `Ctrl+a` | Choose Groq / Choose OpenAI |
| | `Ctrl+l` / `Ctrl+c` | Choose Ollama / Choose Custom API |
| | `Ctrl+d` | Disable AI (strictly offline, local TUI heuristics only) |

### Robust Clipboard Copy System
* **Binding**: Pressing `c` copies the selected text in the details panel to the operating system's clipboard.
* **Mechanism**: To bypass restrictions where terminal emulators do not support or have disabled terminal clipboard escape codes (OSC 52), the TUI implements a dual-layered copy pipeline:
  1. **OS-Level Subprocess**: It attempts to pipe the text directly to OS clipboard binaries (`pbcopy` on macOS, `xclip`/`xsel`/`wl-copy` on Linux, and `clip` on Windows).
  2. **OSC 52 Fallback**: It executes Textual's default `copy_to_clipboard` method which issues ANSI escape sequences to the terminal, allowing support for SSH/remote sessions.
* **ANSI Stripping**: The copy engine automatically cleans raw ANSI styling codes from the selection to ensure only clean, plain text is copied.

### Background Workers
To prevent network requests from freezing the UI, TUI uses Textual's `@work` thread-based async decorators.
The app spawns background query tasks to process LLM request threads. Once completed, they update the `DetailsCanvas` view and the `HistoryTree` node labels.

---

## 11. AI Prompts & Narrative Design Rules

TermStory generates summaries using prompts designed to avoid corporate marketing slop and output high-density, CLI-styled dev logs.

### Prompt Content Rules
1. **High-Density Output**: Restructures the summary into a 3-line ASCII tree/tech bullet log mimicking terminal diagnostics rather than standard paragraph reviews.
2. **Technical Progression**: Sequentially tracks what was built first, what tooling/flow followed next, and the outcome/status of the session.
3. **No Fluff**: Strictly forbids generic filler lines ("Ultimately, the hard work paid off..."). Keeps it direct and technical.
4. **Developer Voice**: Employs active past-tense engineering verbs at the start of each log line (e.g. *wired up, refactored, hacked on, stabilized, shipped*).

### Prompt Templates

#### A. Session Summaries Prompt
```
Translate the developer's raw shell commands and Git commits into a high-density, CLI-styled terminal log of their work session.

YOUR CORE GOAL:
Generate a 3-line bulleted dev log. It must resemble a clean, tech-dense terminal audit output using ASCII connection lines or tech symbols.

Choose ONE of the following formats to return, matching the inputs:

Format Option A (ASCII branch log style):
[💻 Dev Log]
├─ 🔨 Built: <short, punchy action phrase of what was built or coded, using tech keywords>
├─ 🔧 Flow: <brief sequence of tools used, tests run, or configurations edited>
└─ 🚀 Result: <final milestone shipped, fixed, or pushed>

Format Option B (Tech bullet list style):
[🤖 Codebase Pulse]
• Hacked: <what was designed, refactored, or debugged>
• Tooling: <commands run, docker setups, or libraries configured>
• Outcome: <what was successfully verified, resolved, or shipped>

Choose either Option A or Option B at random or based on the inputs to provide variation, but always output EXACTLY the selected format.
Never output any paragraphs of text, conversational filler, markdown formatting, or surrounding quotes. Only return the raw 4 lines of console text.

STYLE & TONE RULES:
1. NO MARKETING FLUFF: Never write paragraphs like 'Ultimately, the hard work paid off...'. Keep it purely developer-centric and density-focused.
2. START WITH ACTION VERBS: Each bullet line must start directly with an active, past-tense engineering verb (e.g., 'wired up', 'refactored', 'debugged', 'spun up', 'implemented').
3. Keep each line extremely concise, informative, and technical.

Input Data to Summarize:
Project: {project_name}
Commands Executed:
{commands_block}
{commits_block}

Output format: Return ONLY the raw, polished console text block. No markdown formatting, no conversational filler, and no surrounding quotes.
```

#### B. Timeframe/Executive Review Prompt
```
Write a highly-personalized, modern engineering review of the developer's work over this entire period based on their commits, session summaries, and tooling stats.

YOUR CORE GOAL:
Generate a high-density, CLI-styled audit review of the timeframe. It must resemble terminal diagnostic output using ASCII connection lines, matching this exact structure:

✨ [⚡ Timeframe Audit]
├─ 📂 <Project A Name>   [XX%]
├─ 📂 <Project B Name>   [XX%]
└─ 📂 Misc / Sys Config  [XX%]

RULES FOR GENERATION:
1. Extract the projects and their percentage distributions from the input context (PROJECTS DISTRIBUTION).
2. List the projects in descending order of percentage.
3. Truncate any projects with less than 5% share or named 'Other', and group their combined percentages into a single final line: '└─ 📂 Misc / Sys Config  [XX%]'.
4. Use the branch characters correctly: '├─ 📂' for all projects except the last one, which must use '└─ 📂'.
5. Keep the alignment neat.
6. Do not output any paragraphs, explanations, conversational filler, markdown formatting, or surrounding quotes. Only return the raw lines of console text.

Developer Work Log Context:
{stats_summary}

Output format: Return ONLY the raw, polished console text block. No markdown formatting, no conversational filler, and no surrounding quotes.
```

---

## 12. CLI Command Reference

### `termstory` / `termstory today`
Queries work done today.
* `termstory` — Display today's timeline grouped by project.
* `termstory today --detailed` — Mute the filters and dump the raw list of all commands in today's sessions with exact timestamps.
* `termstory today --compare` — Display today's summary side-by-side with yesterday's work log.
* `termstory today --stats` — Show a formatted table breaking down command frequencies by category (Git, Docker, Package Managers, Editors, Navigations).

### `termstory search <query>`
Searches your commands, commits, and project names.
* `termstory search docker` — Find all Docker sessions, collapsed by day per project.
* `termstory search docker --project huge` — Filter results to projects matching "huge".
* `termstory search docker --since 2026-05-01` — Return matches since the specified date.
* `termstory search docker --detailed` — Show timestamps and raw executed command logs for the matches.

### `termstory week`
Prints a weekly summary.
* `termstory week` — Display work report for the current week.
* `termstory week --last` — Display work report for last week.
* `termstory week --project hugegraph` — Filter weekly summary to the specific project.

### `termstory month`
Prints a monthly summary.
* `termstory month` — Display summary for the current month.
* `termstory month "May 2026"` — Query data for a specific historical month.
* `termstory month --last` — Query data for the previous month.

### `termstory project <name>`
Prints a 30-day deep dive for a single project.
* `termstory project hugegraph` — Display dates and accomplishments/memories.
* `termstory project hugegraph --files` — List files edited within the project workspace, sorted by frequency.
* `termstory project hugegraph --stats` — Display command stats categories for the project.

### `termstory projects`
Lists all tracked workspaces.
* `termstory projects --sort time` — Sort by cumulative hours (default).
* `termstory projects --sort recent` — Sort by date of last activity.
* `termstory projects --sort name` — Sort alphabetically.

### `termstory insights`
Analyzes patterns.
* `termstory insights --days 90` — Evaluates focus scores, time of day/week distributions, and tool breakdowns for the last 90 days.

### `termstory ui`
Launches the Textual dashboard.
* `termstory ui` — Launches TUI displaying the last 90 days (default).
* `termstory ui --days 30` — Limit history timeline to the last 30 days.
* `termstory ui --all` — Build timeline explorer for all recorded database sessions.

### `termstory config`
* `termstory config list` — Print all current settings, masking API keys.
* `termstory config get active_provider` — Retrieve a configuration value.
* `termstory config set active_provider ollama` — Write a configuration parameter.

### Date Override Env
You can query historical dates directly:
* `termstory 2026-05-15` — Summary for May 15th, 2026.
* `termstory --date 2026-05-15 week` — Weekly report for the week containing May 15th, 2026.

---

## 13. Configuration Reference (`config.json`)

The config file is located at `~/.termstory/config.json`. Below is the complete structured representation of the settings:

```json
{
    "ai_enabled": false,
    "active_provider": "disabled",
    "has_seen_onboarding": false,
    "providers": {
        "groq": {
            "api_key": "gsk_...",
            "api_base_url": "https://api.groq.com/openai/v1",
            "model_name": "llama-3.1-8b-instant"
        },
        "openai": {
            "api_key": "sk-proj-...",
            "api_base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini"
        },
        "ollama": {
            "api_key": "",
            "api_base_url": "http://localhost:11434/v1",
            "model_name": "llama3"
        }
    }
}
```

### Configuration Dot Paths
You can query and edit settings using dot notation paths via `termstory config set <path> <value>`.

Supported paths:
* `ai_enabled` (boolean: `true`/`false`)
* `active_provider` (string: `"groq"`, `"openai"`, `"ollama"`, `"disabled"`)
* `has_seen_onboarding` (boolean: `true`/`false`)
* `providers.groq.api_key` (string)
* `providers.groq.api_base_url` (string)
* `providers.groq.model_name` (string)
* `providers.openai.api_key` (string)
* `providers.openai.api_base_url` (string)
* `providers.openai.model_name` (string)
* `providers.ollama.api_key` (string)
* `providers.ollama.api_base_url` (string)
* `providers.ollama.model_name` (string)

---

## 14. Developer Verification & Testing Suite

TermStory uses `pytest` for unit and integration testing.

### Running Tests
Run the following command from the project root:
```bash
python3 -m pytest tests/
```

### Test Directory Breakdown

* `test_parser.py`: Verifies Zsh history format matching, bash modifications, and spacing heuristics.
* `test_session.py`: Tests the 30-minute grouping calculations, session boundaries, and duration logic.
* `test_project.py`: Asserts project path resolution, Git folder matching, file parsers, and "Other" mappings.
* `test_git_integration.py`: Mocks Git command outputs and verifies message cleaning.
* `test_database.py` & `test_database_queries.py`: Tests connection PRAGMAs, SQL queries, inserts, and caches.
* `test_sanitizer.py`: Verifies credential, token, IP, and hostname redaction rules.
* `test_ai.py`: Validates the custom `urllib.request` payload construction and mocking scenarios.
* `test_tui.py`: Spawns Textual test runners to simulate keyboard presses, help modals, onboarding flow screens, and tree navigation updates.
* `test_formatter_rich.py`: Asserts console command output rendering.

---

## 15. Troubleshooting & Personal Customization Hacks

### A. Reset to a Clean Slate
To reset the tool's history, cached summaries, and configuration, remove the local files:
```bash
rm -rf ~/.termstory/
```
The next command execution or TUI launch will initialize a new database and display the onboarding screen.

### B. Manually Trigger History Sync
If new command lines or commits are not showing up, run:
```bash
python3 -m termstory.cli today --detailed
```
This forces a file read and updates the local SQLite tables.

### C. Enable Local AI (Ollama Setup)
1. Ensure Ollama is running locally:
   ```bash
   ollama run llama3
   ```
2. Open the TUI:
   ```bash
   termstory ui
   ```
3. Press `o` to open the AI configuration panel.
4. Select Ollama (press `Ctrl+L`).
5. Set the model name to `llama3` and save. The tool will begin querying the local instance for summaries.
