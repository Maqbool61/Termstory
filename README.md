# TermStory — Your Personal Developer Memory Engine

> Parse your shell history. Recover your past. Understand your work.

TermStory turns your terminal history into a searchable, AI-narrated timeline of your development life. It groups shell commands into sessions, correlates Git commits, resolves project names, and renders everything into a high-density TUI dashboard — with a built-in forensic engine that can **recover the real dates of commands you typed before you even knew timestamps were missing**.

```
pip install termstory
termstory ui
```

---

## Table of Contents

1. [Core Philosophy](#1-core-philosophy)
2. [Installation & Quick Start](#2-installation--quick-start)
3. [Project Layout](#3-project-layout)
4. [The Ingestion Pipeline](#4-the-ingestion-pipeline)
5. [Shell History Parsing](#5-shell-history-parsing)
6. [The Timestamp Detective (v0.2.9)](#6-the-timestamp-detective-v029)
7. [Project Resolution](#7-project-resolution)
8. [Git Commit Correlation](#8-git-commit-correlation)
9. [Database Schema](#9-database-schema)
10. [Privacy Sanitizer](#10-privacy-sanitizer)
11. [AI Client](#11-ai-client)
12. [TUI Dashboard](#12-tui-dashboard)
13. [AI Narrative Design](#13-ai-narrative-design)
14. [CLI Reference](#14-cli-reference)
15. [Configuration](#15-configuration)
16. [Testing](#16-testing)
17. [Troubleshooting](#17-troubleshooting)

---

## 1. Core Philosophy

TermStory is **not** a tracking tool, a productivity auditor, or a corporate analytics dashboard. It is a **personal developer memory engine** built on three ideas:

- **Recognize, don't inspect.** The goal is instant recognition — *"Ah, that was the day I fought the Docker networking bug"* — not a wall of `cd` and `ls` entries. Noise commands are filtered automatically.
- **Density over decoration.** No rounded panels, no double borders, no empty margins. Clean column alignment, tight spacing, information-first.
- **Screenshot-friendly.** Every view fits in one terminal screen and tells a complete, self-contained story.

---

## 2. Installation & Quick Start

**Requirements:** Python 3.9+, a terminal with `zsh` or `bash`.

```bash
pip install termstory
```

### Enable timestamps (zsh only — one time setup)

TermStory works best when your shell records timestamps. If you haven't done this already:

```bash
echo '\nsetopt EXTENDED_HISTORY\nsetopt HIST_STAMPS="yyyy-mm-dd"' >> ~/.zshrc
source ~/.zshrc
```

> **Already have old history without timestamps?** TermStory's Timestamp Detective (v0.2.9) will forensically recover real dates from your git log, filesystem metadata, and package manager artifacts automatically. You don't lose your past.

### First launch

```bash
termstory ui          # Interactive TUI dashboard (recommended)
termstory today       # Today's timeline in the terminal
termstory search auth # Search across all history
```

On first launch, TermStory detects whether you have timestamps enabled. If not, it offers to enable `EXTENDED_HISTORY` automatically. You can skip this and proceed anyway — the Timestamp Detective will handle your legacy history.

---

## 3. Project Layout

```
termstory/
├── setup.py                     # Package metadata
├── pyproject.toml               # Build config
├── README.md                    # This document
├── DATA_PRIVACY.md              # LLM data handling policy
├── termstory/
│   ├── __init__.py              # Version: 0.2.9
│   ├── __main__.py              # python3 -m termstory entry point
│   ├── cli.py                   # Typer CLI — all commands & ingestion entry point
│   ├── tui.py                   # Textual TUI dashboard & all widgets
│   ├── parser.py                # Shell history parsing engine
│   ├── timestamp_detective.py   # v0.2.9 — forensic timestamp recovery engine
│   ├── session.py               # 30-minute session grouping
│   ├── project.py               # VCS root detection & project name resolution
│   ├── git_integration.py       # git log subprocess client & commit cleaner
│   ├── database.py              # SQLite layer (WAL, schema, queries, cache)
│   ├── date_utils.py            # Timezone & timestamp utilities
│   ├── sanitizer.py             # Local credential & PII redaction
│   ├── ai.py                    # Zero-dependency LLM client (urllib only)
│   ├── insights.py              # Focus score & pattern calculations
│   ├── models.py                # Command, Session, Project, Commit dataclasses
│   └── formatter.py            # CLI output layout & Rich styling
└── tests/
    ├── fixtures/
    │   └── sample_history.txt
    ├── test_parser.py
    ├── test_session.py
    ├── test_project.py
    ├── test_git_integration.py
    ├── test_database.py
    ├── test_database_queries.py
    ├── test_sanitizer.py
    ├── test_ai.py
    ├── test_tui.py
    ├── test_formatter_rich.py
    ├── test_insights.py
    ├── test_timestamp_detective.py  # v0.2.9 — 155 tests
    └── test_integration.py
```

---

## 4. The Ingestion Pipeline

Every CLI command and every TUI launch runs this pipeline:

```
~/.zsh_history / ~/.bash_history
         │
         ▼
    parser.py  ──────────────────────────────────────────────────────────┐
    Parse raw history into Command objects.                               │
    Separate timestamped commands from legacy (no-timestamp) commands.   │
         │                                                                │
         ▼  (legacy commands only)                                        │
    timestamp_detective.py                                                │
    Phase A: Replay cd/pushd/popd → virtual CWD per command              │
    Phase B: 5 forensic detectors (git log, file stat, pkg mgr,          │
             docker, lockfiles) → real timestamps + Chain of Custody      │
    Phase C: Anchor Interpolation → linear fill between anchors          │
         │                                                                │
         └─────────────────────────────────────────────────────────────►─┤
         ▼                                                                │
    session.py                                                            │
    Group commands into sessions (30-minute idle threshold)              │
         │                                                                │
         ▼                                                                │
    project.py                                                            │
    Detect VCS root → extract project name from manifests → "Other"      │
         │                                                                │
         ▼                                                                │
    git_integration.py                                                    │
    Run git log for session timeframe → clean commit messages            │
         │                                                                │
         ▼                                                                │
    sanitizer.py                                                          │
    Redact credentials, IPs, tokens before any AI call                   │
         │                                                                │
         ▼                                                                │
    database.py  →  ~/.termstory/termstory.db (SQLite + WAL)            │
    Store sessions, commands, commits, recovery_source, AI cache         │
         │                                                                │
         ▼                                                                │
    tui.py / formatter.py                                                 │
    Render timeline, badges, AI summaries, Chain of Custody tooltips     │
```

---

## 5. Shell History Parsing

### Zsh — EXTENDED_HISTORY format

When `setopt EXTENDED_HISTORY` is enabled, Zsh writes:

```
: 1717500000:3;git commit -m "fix auth"
```

The parser extracts timestamp, duration, and command text with multiline support (trailing `\` continuation).

### Zsh — Hybrid / Frankenstein Mode

If you recently enabled `EXTENDED_HISTORY`, your `~/.zsh_history` contains a mix of timestamped and legacy lines. The parser handles this automatically:

- Timestamped lines are extracted normally.
- Legacy lines are collected separately.
- The oldest timestamped command's timestamp minus 60 seconds becomes the `anchor_time`.
- **The Timestamp Detective runs on all legacy lines** (see Section 6).
- **Timestamp Locking**: On subsequent runs, synthetic timestamps are looked up in the database and re-used to prevent legacy commands from shifting dates.

### Bash — HISTTIMEFORMAT

If `HISTTIMEFORMAT` is set, Bash writes `#<timestamp>` headers before each command. The parser associates each command with its preceding timestamp header. Without headers, timestamps are spaced 10 seconds apart backward from the file's `mtime`.

### Filtering

Commands older than 5 years or with future timestamps are silently dropped to prevent database pollution.

---

## 6. The Timestamp Detective (v0.2.9)

> The most significant feature in TermStory's history. If you've been using your terminal for years without `EXTENDED_HISTORY`, your shell history has no dates at all — every command appears to have happened "today". The Timestamp Detective reverse-engineers real timestamps by mining your git log, filesystem metadata, and package manager artifacts.

### The Problem

Without `EXTENDED_HISTORY`, a file like Vansh's 847-command history gets anchored to "today" via a 1-second step-back. His March commits, April npm installs, and May docker builds all collapse into one meaningless session labelled *today*.

### The Solution — Three Phases

#### Phase A — Virtual CWD Tracker

Before running any detector, the engine replays `cd`, `pushd`, and `popd` commands in sequence to compute the **virtual working directory** at every point in history. This is critical because git commit searches must be scoped to the correct repository — otherwise `git commit -m "fix typo"` could match a commit from the wrong project.

```
idx 0:  ls                     → cwd = "~"
idx 1:  cd ~/Projects/myapp    → cwd = "~/Projects/myapp"
idx 2:  npm install            → cwd = "~/Projects/myapp"
idx 3:  git commit -m "init"   → cwd = "~/Projects/myapp"  ← searches THIS repo only
idx 4:  cd ..                  → cwd = "~/Projects"
```

Supports: `cd -` (previous dir), relative `..` paths, `~` and `$HOME` expansion, `pushd`/`popd` stack.

#### Phase B — Five Forensic Detectors

Run in priority order. Each returns `(unix_timestamp, source_string)` or `None`.

**1. Git Commit Matcher** ⭐ Highest confidence

Extracts the message from `git commit -m "…"` and runs `git log --all` on the CWD-scoped repository. Fuzzy-matches the message using `difflib.SequenceMatcher` with a threshold of ≥ 0.85 after stripping conventional prefixes (`feat:`, `fix(scope):`) and emojis from both sides.

**Multi-Repo Collision Trap:** The CWD-derived repo is searched first. If Vansh has three repos with `git commit -m "fix typo"`, only the repo he was sitting in when he typed it gets matched. Fallback to other known project paths only if the local repo has no match.

**2. File Stat** 🟡 Medium confidence

Stats the artifact created by file-creating commands:

| Command | Target |
|---|---|
| `touch <file>` | `<file>` — `st_birthtime` (macOS) or `st_mtime` |
| `mkdir [-p] <dir>` | `<dir>` |
| `echo/printf/cat > <file>` | redirect target |
| `cp <src> <dst>` | `<dst>` |
| `git init [dir]` | `<dir>/.git` |
| `npm init [-y]` | `cwd/package.json` |
| `python -m venv <name>` | `<name>/bin/activate` |
| `cargo init [dir]` | `<dir>/Cargo.toml` |
| `go mod init` | `cwd/go.mod` |

`touch -t` (explicit timestamp set) is excluded. All paths are resolved against the virtual CWD.

**3. Package Manager Install Metadata** 🟡 Medium confidence

| Command | Artifact |
|---|---|
| `brew install <formula>` | `$(brew --prefix)/Cellar/<formula>` mtime |
| `pip install <pkg>` | pip dist-info directory mtime |
| `npm install` (local) | `package-lock.json` mtime |
| `npm install -g <pkg>` | global node_modules `/<pkg>` mtime |
| `cargo add/install <crate>` | `~/.cargo/registry/src/*/*crate*` mtime |
| `gem install <gem>` | `~/.gem/ruby/*/gems/<gem>-*` mtime |

Both `brew --prefix` and `npm root -g` subprocess calls are cached after the first call.

**4. Docker Image Inspector** 🟡 Medium confidence

For `docker build -t <tag>` commands, runs:
```bash
docker image inspect <tag> --format='{{.Created}}'
```
Parses the RFC3339 timestamp and returns the exact second the image was built.

**5. Venv / Lockfile Sentinels** 🟡 Low-medium confidence

| Command | Artifact |
|---|---|
| `bundle install` | `Gemfile.lock` mtime |
| `go mod tidy` / `go get` | `go.sum` mtime |
| `composer install` | `composer.lock` mtime |
| `poetry add/install` | `poetry.lock` mtime |
| `mix deps.get` | `mix.lock` mtime |
| `git clone <url> [dir]` | `<dir>/.git` birthtime |
| `ssh-keygen -f <file>` | `<file>` birthtime |

#### Phase C — Anchor Interpolation Engine ⭐ The Killer Feature

After Phase B, some commands have real timestamps (anchors) and others are still `None`. For each contiguous gap between two anchors, unresolved commands are distributed **linearly**:

```
t_i = t_a + (t_b − t_a) × (i − i_a) / (i_b − i_a)
```

**Example:**

```
[500] npm install express     → 🔍 ANCHOR  Tuesday 14:00  (package.json mtime)
[501] npm start               → 📐 INTERP  Tuesday 14:07  (between anchors)
[502] git commit -m "add express" → 🔍 ANCHOR Tuesday 14:15  (git log)
```

`npm start` is mathematically placed at 14:07 — the proportional moment between the two known events. Not a guess, not today — the most likely real time.

- **Prefix gap** (before first anchor): 1-second step-back from anchor.
- **Suffix gap** (after last anchor): 1-second step-forward from anchor.
- **No anchors at all**: original mtime step-back (same as v0.2.8 behaviour).

### Chain of Custody — The Trust Badge

Every command that the Detective recovered gets a `recovery_source` string persisted to the database. In the TUI, it renders as a badge below the command:

```
💻 Command Timeline:
  • 14:00:03  npm install express
      [🔍 stat: package.json mtime]
  • 14:07:31  npm start
      [🔍 Interpolated (between stat: package.json mtime → git log: myapp@a3f9b2c)]
  • 14:15:44  git commit -m "add express"
      [🔍 git log: myapp@a3f9b2c]
```

This turns *"how the hell did it know that?"* into a *"holy crap, this app is smart"* moment.

### TUI Session Labels

| Label | Meaning |
|---|---|
| `✨ npm init, express installed  (14:00 - 14:45)` | Real EXTENDED_HISTORY timestamp |
| `🔍 Recovered Archive (38 cmds • 14:00 - 14:45)` | Detective found anchors + interpolated |
| `📦 Legacy Archive (12 recovered cmds)` | Zero forensic evidence, fully synthetic |

---

## 7. Project Resolution

`project.py` maps a working directory to a human-readable project name using a two-pass strategy:

```
Working Directory: /home/dev/Projects/termstory/tests
         │
         ▼
Walk up directories looking for .git / .hg / .svn
         │
         ▼
Found root: /home/dev/Projects/termstory
         │
         ▼
Read build manifests:
  package.json → "name" field
  Cargo.toml   → [package] name
  setup.py     → name= argument
  pom.xml      → <artifactId>
         │
         ▼
Normalize: strip hyphens, fix casing
Result: "termstory"
```

**Fallback strictness:** If a directory is not inside a standard project root (`~/Projects/`, `~/src/`, etc.) and has no VCS markers, it maps to the user's home directory and is grouped under `"Other"`. This prevents `~/.ssh`, `~/Downloads`, or `/tmp` from polluting the project list.

---

## 8. Git Commit Correlation

`git_integration.py` enriches sessions by fetching matching commits:

```bash
git -C <repo_root> log --all \
    --since="<session_start - 5min>" \
    --until="<session_end + 10min>" \
    --format="%H|%at|%s"
```

**Commit cleaning pipeline:**
- Strips conventional commit prefixes (`feat(scope):`, `fix:`, `chore:`)
- Removes Unicode emoji and `:shorthand:` tokens
- Drops merge commit messages and branch pointer refs
- Stores both raw and cleaned message for AI prompts

---

## 9. Database Schema

`~/.termstory/termstory.db` — SQLite with WAL mode (`PRAGMA journal_mode = WAL`).

```sql
CREATE TABLE projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    path        TEXT,
    first_seen  INTEGER,
    last_seen   INTEGER,
    created_at  INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time       INTEGER NOT NULL,
    end_time         INTEGER NOT NULL,
    duration_seconds INTEGER,
    project_id       INTEGER REFERENCES projects(id),
    ai_summary       TEXT,       -- Cached AI narrative; reused across runs
    created_at       INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE commands (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       INTEGER NOT NULL,
    command         TEXT NOT NULL,
    exit_code       INTEGER,
    session_id      INTEGER REFERENCES sessions(id),
    project_id      INTEGER REFERENCES projects(id),
    recovery_source TEXT,    -- v0.2.9: Chain of Custody attribution string, NULL for real timestamps
    created_at      INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE commits (
    hash            TEXT PRIMARY KEY,
    timestamp       INTEGER NOT NULL,
    message         TEXT NOT NULL,
    cleaned_message TEXT NOT NULL,
    project_id      INTEGER REFERENCES projects(id),
    created_at      INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE macro_summaries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timeframe_id TEXT NOT NULL UNIQUE,  -- e.g. "2026-06-03" or "June 2026" or "overall"
    type         TEXT NOT NULL,         -- "date", "month", or "overall"
    summary      TEXT NOT NULL,
    created_at   INTEGER DEFAULT (strftime('%s', 'now'))
);
```

**Indexes:** `idx_commands_timestamp`, `idx_commands_session_id`, `idx_sessions_start_time`, `idx_sessions_project_id`, `idx_sessions_date_range`, `idx_commits_timestamp`, `idx_commits_project_id`, `idx_sessions_project_date`.

**Deduplication:** Unique constraints on `sessions(start_time)` and `commands(timestamp, command)` prevent re-ingestion duplicates. One-time migration cleans any pre-constraint duplicates on first upgrade.

---

## 10. Privacy Sanitizer

All data passes through `sanitizer.py` **locally** before any AI call. Nothing sensitive ever leaves your machine.

### Session Blacklist

If any command in a session matches these patterns, the entire session is short-circuited to return `"Security/Authentication Operations"` — no commands are sent to the LLM at all:

```python
BLACKLIST_PATTERNS = [
    r'\bvault\b',
    r'\baws\s+configure\b',
    r'\bgh\s+auth\b',
    r'\bkubectl\s+.*?\bcreate\s+secret\b',
]
```

### Redaction Rules

| Type | Pattern | Replacement |
|---|---|---|
| Private keys | `-----BEGIN ... PRIVATE KEY-----` | `[REDACTED_PRIVATE_KEY]` |
| AWS keys | `AKIA[A-Z0-9]{16}` | `[REDACTED_AWS_KEY]` |
| Bearer tokens | `bearer <token>` | `Bearer [REDACTED_TOKEN]` |
| Flag values | `--password`, `--token`, `--api-key`, `-p` | `--password=[REDACTED]` |
| IPv4/IPv6 | standard address patterns | `[REDACTED_IP]` |
| Hostnames/FQDNs | `host.domain.tld` | `[REDACTED_HOST]` |
| Exports | `export KEY=value` | `export KEY=[REDACTED]` |

**File extension whitelist:** Paths ending in `.py`, `.json`, `.sh`, `.yml`, `.ts`, `.go`, etc. are never redacted even if they look like FQDNs — preserving filenames like `config.json` and `api.ts`.

---

## 11. AI Client

`ai.py` interfaces with any OpenAI-compatible LLM endpoint using **only Python's standard library** — no `requests`, no `openai-python`.

- **Transport:** `urllib.request.Request` with JSON payload
- **URL normalization:** Strips trailing slashes, auto-appends `/chat/completions`
- **Keyless mode:** Skips `Authorization: Bearer` header if API key is empty (Ollama compatibility)
- **Timeout:** 15 seconds to prevent blocking the TUI thread
- **Background execution:** All AI calls run in Textual `@work` async workers — UI never freezes

### Supported Providers

| Provider | Default model | Notes |
|---|---|---|
| **Groq** | `llama-3.1-8b-instant` | Fast, free tier available |
| **OpenAI** | `gpt-4o-mini` | Requires API key |
| **Ollama** | `llama3` | Fully local, no key needed |
| **Custom** | any | Any OpenAI-compatible endpoint |

---

## 12. TUI Dashboard

Launch with `termstory ui`.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔥 12 day streak  •  43 active days  •  127h 14m total                     │
│  Activity (Last 90 Days):  ░░▒▒░▓▓█▓▒░░▒▒▓▓█▓▒░░▒▓▓█▓▒░░▒▒▓▓█▓▒░░▒░░      │
├───────────────────────────────┬─────────────────────────────────────────────┤
│  June 2026                    │  📂 termstory  •  Tue Jun 03                │
│  ├─ Jun 07 (Sat)              │  ─────────────────────────────────────────  │
│  │  └─ termstory              │  [💻 Dev Log]                               │
│  │     ✨ v0.2.9 Timestamp… │  ├─ 🔨 Built: Timestamp Detective with      │
│  ├─ Jun 06 (Fri)              │         5 forensic detectors & interpolation│
│  │  ├─ termstory              │  ├─ 🔧 Flow: pytest 155 passed, twine      │
│  │  └─ Other                  │         upload, git push origin main        │
│  │     📦 Legacy Archive      │  └─ 🚀 Result: v0.2.9 published to PyPI    │
│  └─ Jun 05 (Thu)              │                                             │
│     └─ 🔍 Recovered Archive   │  💻 Command Timeline:                       │
│                               │  • 00:47:57  git commit -m "feat: v0.2.9…" │
│                               │      [🔍 git log: termstory@bbe9dfc]        │
│                               │  • 00:48:12  python3 -m pytest tests/       │
│                               │  • 00:49:03  twine upload dist/*            │
└───────────────────────────────┴─────────────────────────────────────────────┘
  ?:help  /:search  o:ai-config  c:copy  q:quit
```

### Layout

- **StatsHeader** (top, full-width): streak count, active days, total duration, and a GitHub-style command-volume heatmap synced to the timeline's `--days` limit.
- **HistoryTree** (left 30%): collapsible Year → Month → Day → Project → Session tree. The root node shows an All-Time Wrapped dashboard. Month nodes show Monthly Wrapped.
- **DetailsCanvas** (right 70%): renders whatever the selected tree node points to — date chronicle, session details, wrapped views, or search results.

### Session Tree Labels

```
✨ npm init, express installed  (14:00 - 14:45)   ← real timestamp
🔍 Recovered Archive (38 cmds • 14:00 - 14:45)    ← Detective recovered
📦 Legacy Archive (12 recovered cmds)              ← fully synthetic
```

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `?` | Toggle help overlay |
| `/` | Open search box (real-time filter of 90-day window) |
| `Enter` (in search) | Escape to all-time deep search |
| `Esc` | Close modal / clear search / restore timeline |
| `o` | Open AI provider configuration screen |
| `c` | Copy selected canvas content to OS clipboard |
| `j` / `k` / `↑` / `↓` | Navigate tree |
| `Ctrl+↓` / `Ctrl+↑` | Scroll canvas |
| `q` | Quit |

### Search Engine

Typing in `/` search filters the pre-loaded 90-day timeline in real-time (no DB hit). Pressing `Enter` escapes to an all-time database search across commands, commit messages, project names, and AI summaries. The tree root label changes to `🔍 Search Results: "query"`. Pressing `Esc` or clearing the box instantly restores the original timeline.

### Clipboard

`c` pipes text directly to `pbcopy` (macOS), `xclip`/`xsel`/`wl-copy` (Linux), or `clip` (Windows), bypassing OSC 52 terminal restrictions. ANSI escape codes are stripped before copy.

### Onboarding

On first launch with no config, an interactive onboarding screen offers `Ctrl+G` (Groq), `Ctrl+A` (OpenAI), `Ctrl+L` (Ollama), `Ctrl+C` (Custom), or `Ctrl+D` (disable AI). If your history lacks timestamps, a consent prompt offers to append `setopt EXTENDED_HISTORY` to `~/.zshrc`.

### Wrapped Views

Selecting the root **Timeline** node or a **Month** node shows a high-density wrapped dashboard:

- **Code churn matrix:** git insertions vs. deletions, net LOC growth
- **Time distribution:** hourly activity punch-card across the period
- **Project breakdown:** percentage distribution across all projects
- **Top commits & tooling:** most-used commands, editors, languages
- **AI Behavioral Audit:** a witty, witty roast of your patterns and productivity archetypes (*"The Midnight Alchemist"*, *"The Expansionist Architect"*) — regeneratable with `r`

---

## 13. AI Narrative Design

TermStory's prompts are designed to produce **high-density, CLI-styled developer logs** — not marketing prose.

### Session Summary Format

```
[💻 Dev Log]
├─ 🔨 Built: <short punchy action — what was built or coded>
├─ 🔧 Flow: <tools used, tests run, configs edited>
└─ 🚀 Result: <milestone shipped, fixed, or pushed>
```

or:

```
[🤖 Codebase Pulse]
• Hacked: <what was designed, refactored, or debugged>
• Tooling: <commands run, docker setups, libraries configured>
• Outcome: <what was verified, resolved, or shipped>
```

**Rules enforced in the prompt:**
- No paragraphs. No filler. No "ultimately the hard work paid off".
- Every line starts with a past-tense engineering verb: *wired up, refactored, debugged, spun up, stabilized, shipped*.
- Second-person narrative (`"You"`) for the Daily Chronicle view.

### Daily Chronicle (Date node)

When a date is selected in the TUI, a full "Story of You" daily narrative is generated — including an inferred breaks timeline, hourly activity punch-card, and second-person storytelling of the whole day.

---

## 14. CLI Reference

### Daily

```bash
termstory                    # Today's timeline
termstory today              # Same as above
termstory today --detailed   # All commands, no noise filtering, with timestamps
termstory today --compare    # Side-by-side with yesterday
termstory today --stats      # Command category frequency table
```

### Search

```bash
termstory search <query>
termstory search docker
termstory search docker --project myapp
termstory search docker --since 2026-05-01
termstory search docker --detailed
```

### Historical

```bash
termstory week               # Current week
termstory week --last        # Previous week
termstory month              # Current month
termstory month "May 2026"   # Specific month
termstory month --last       # Previous month
```

### Projects

```bash
termstory project <name>             # 30-day deep dive
termstory project myapp --files      # Files edited, by frequency
termstory project myapp --stats      # Command category breakdown
termstory projects                   # All tracked projects
termstory projects --sort time       # By total hours (default)
termstory projects --sort recent     # By last active date
termstory projects --sort name       # Alphabetically
```

### Insights

```bash
termstory insights           # Focus scores, time-of-day distribution, tool breakdown
termstory insights --days 90 # Over the last 90 days
```

### TUI

```bash
termstory ui                 # Full dashboard, last 90 days
termstory ui --days 30       # Limit to last 30 days
termstory ui --all           # All history
```

### Config

```bash
termstory config list
termstory config get active_provider
termstory config set active_provider groq
termstory config set providers.groq.api_key gsk_...
```

### Date override

```bash
termstory 2026-05-15                 # Specific date
termstory --date 2026-05-15 week     # Week containing that date
```

---

## 15. Configuration

Config lives at `~/.termstory/config.json`:

```json
{
    "ai_enabled": true,
    "active_provider": "groq",
    "has_seen_onboarding": true,
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
        },
        "custom": {
            "api_key": "",
            "api_base_url": "http://localhost:8080/v1",
            "model_name": "my-model"
        }
    }
}
```

All settings are editable via `termstory config set <dot.path> <value>`.

---

## 16. Testing

```bash
python3 -m pytest tests/ -v
```

**v0.2.9 results: 155 passed, 1 skipped, 0 failures**

| Test File | What it covers |
|---|---|
| `test_parser.py` | Zsh format extraction, hybrid mode, bash fill algorithm, multiline commands |
| `test_timestamp_detective.py` | Virtual CWD tracker, all 5 detectors, anchor interpolation, full pipeline |
| `test_session.py` | 30-minute grouping, boundary detection, duration calculation |
| `test_project.py` | VCS root climbing, manifest parsing, "Other" fallback, home dir strictness |
| `test_git_integration.py` | `git log` subprocess mocking, commit message cleaning |
| `test_database.py` / `test_database_queries.py` | WAL config, schema init, CRUD, dedup migration, date range queries |
| `test_sanitizer.py` | Blacklist short-circuit, credential redaction, FQDN exclusion |
| `test_ai.py` | urllib payload construction, keyless mode, timeout, prompt templates |
| `test_tui.py` | Textual widget lifecycle, onboarding flow, search, wrapped view, clipboard |
| `test_formatter_rich.py` | CLI output layout and Rich markup |
| `test_integration.py` | End-to-end ingestion → DB → render |

---

## 17. Troubleshooting

### Reset everything

```bash
rm -rf ~/.termstory/
termstory ui   # Fresh start, re-runs onboarding
```

### Force a re-ingest

```bash
termstory today --detailed
```

Reads the history file fresh and updates the database.

### Enable EXTENDED_HISTORY manually

```bash
echo '\nsetopt EXTENDED_HISTORY' >> ~/.zshrc
source ~/.zshrc
```

Future commands will get real timestamps. The Timestamp Detective handles everything you typed before enabling this.

### Local AI (Ollama)

```bash
ollama pull llama3
ollama run llama3
termstory ui   # Press 'o' → Ctrl+L to select Ollama
```

### My old history all shows up as "today"

This is expected if you never had `EXTENDED_HISTORY`. The Timestamp Detective will recover what it can using git commits, file stat, and package manager artifacts. Commands it can't place with evidence are grouped in `📦 Legacy Archive` or `🔍 Recovered Archive` in the TUI.

### The detective didn't recover my history

The Detective needs forensic artifacts — git repos, installed packages, or created files — that still exist on disk. If you've wiped your machine since typing those commands, the artifacts are gone and full recovery isn't possible. Enable `EXTENDED_HISTORY` now so this doesn't happen going forward.

---

## License

MIT © TermStory Contributors

**GitHub:** https://github.com/bitflicker64/Termstory  
**PyPI:** https://pypi.org/project/termstory/
