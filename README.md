# TermStory

**Your personal engineering memory.**

TermStory parses your local shell history, groups commands into work sessions, maps Git commits, and turns it all into a searchable timeline of what you actually worked on — not what commands you ran.

```
$ termstory search docker

Docker

15h 28m across 28 sessions
Apr 02 → Jun 02

Apache HugeGraph
────────────────────

May 31  Fix docker process supervision
May 30  git checkout -b fix/docker-process-supervision
May 17  docker run --rm --entrypoint /bin/bash hugegraph-server-new:test...
May 14  git commit -m "perf(docker): improve pd/store/server image build..."
Apr 22  docker compose -f docker-compose-3pd-3store-3server.yml up

Ofbiz Framework
────────────────────

May 06  docker-compose build

Projects
────────────────────

Apr 11  kind load docker-image rishihood-controller:latest
```

Search "docker" and instantly see your Docker journey — which projects, what work, over what period. Not 100 raw `docker ps` rows.

---

## Philosophy

TermStory optimizes for **recognition**, not inspection.

When you search your history, you don't remember:

```
May 31
11:15
1h40m
```

You remember:

```
Oh yeah — that was when I fixed the HugeGraph Docker supervision issue.
```

TermStory surfaces **memories** (commits, meaningful commands, or AI-generated stories), filters **noise** (`cd`, `ls`, `docker ps`, `git status`), and collapses results to **one line per day per project**.

Default output answers: *"What work did I do?"*
`--detailed` output answers: *"How do you know?"*

---

## Features

- 🔍 **Memory-First Search** — Search across commands, commits, and projects. Noise is filtered, commits are prioritized, results are collapsed by day. One screen, not a wall of text.
- 📁 **Project Detection** — Extracts working directories from `cd` commands. Finds Git/Mercurial/SVN roots and project config files (`pom.xml`, `package.json`, etc.). Humanizes names (`incubator-hugegraph` → `Apache HugeGraph`).
- ⏱️ **Session Grouping** — Clusters commands into sessions based on 30-minute activity gaps.
- 💬 **Git Commit Integration** — Maps local Git commits to active sessions using timestamp windowing. Cleans commit messages by stripping emojis, JIRA codes, and conventional prefixes (`feat:`, `fix:`).
- 💡 **Developer Insights** — Focus scores, project time splits, hourly/daily work distribution, and pattern detection.
- 📋 **Daily / Weekly / Monthly Summaries** — Structured breakdowns of where your time went.
- 💻 **Interactive TUI Dashboard** — Live terminal user interface featuring a timeline tree explorer, dynamic search/filter, top statistics panel with a GitHub-style activity heatmap, and a detailed session inspector (defaults to 90 days of history).
- 🤖 **On-Demand AI & Privacy Architecture** — Optional AI categorizations powered by Groq, OpenAI, Ollama, or Custom endpoints. Generates "Executive Summaries" of your week/month and "Session Stories". Protected by a strict `sanitizer` pipeline that drops authentication commands and redacts passwords/IPs/FQDNs locally before any data leaves your machine. 
- 🔒 **100% Local & Private by Default** — Everything stored in a local SQLite database (`~/.termstory/termstory.db`). AI is strictly opt-in and configurable.

---

## Installation

```bash
pip install -e .
```

Or install dependencies manually:

```bash
pip install -r requirements.txt
```

**Requirements:** Python 3.9+, `rich`, `typer`, `python-dateutil`, `textual`

---

## Commands

### `termstory` / `termstory today`

What did I do today?

```bash
termstory               # defaults to today
termstory today
termstory today --detailed   # show all commands in each session
termstory today --compare    # compare with yesterday
termstory today --stats      # command category breakdown table
```

### `termstory search <query>`

Search your entire work history — commits, commands, projects.

```bash
termstory search docker
termstory search docker --detailed        # show timestamps, durations, raw commands
termstory search docker --project huge    # filter by project
termstory search docker --since 2026-05-01
termstory search docker --limit 20
```

Default mode shows **memories** (commit messages, AI stories, meaningful commands), grouped by project, one per day.

### `termstory week`

Weekly work report with day-by-day breakdown.

```bash
termstory week
termstory week --last             # last week
termstory week --project huge     # filter by project
```

### `termstory month`

Monthly summary — logged days, project time, averages.

```bash
termstory month
termstory month "May 2026"    # specific month
termstory month --last        # last month
```

### `termstory project <name>`

30-day deep dive into a specific project.

```bash
termstory project hugegraph
termstory project hugegraph --files     # files you edited
termstory project hugegraph --stats     # command breakdown
termstory project hugegraph --since 2026-04-01
```

### `termstory projects`

List all tracked projects.

```bash
termstory projects
termstory projects --sort recent    # sort by last activity
termstory projects --sort name      # sort alphabetically
termstory projects --sort time      # sort by total hours (default)
```

### `termstory insights`

Focus score, project distribution, work patterns.

```bash
termstory insights
termstory insights --days 90    # analyze last 90 days
```

### `termstory ui`

Launch the interactive Terminal User Interface (TUI) dashboard.

```bash
termstory ui                  # display last 90 days of history (default)
termstory ui --days 30        # display last 30 days
termstory ui --all            # display all recorded history
```

**Key Bindings:**
- `j` / `k` (or Arrow keys): Navigate Timeline Explorer (left tree)
- `Enter` / `Space`: Toggle nodes (expand/collapse)
- `/`: Open dynamic search/filter input
- `Esc` (inside search): Close search and clear filter
- `o`: Open AI Configuration Onboarding Screen
- `q` / `Esc` (inside tree): Exit dashboard
- `Ctrl+Up` / `Ctrl+Down` (or PgUp/PgDn): Scroll Details panel

### `termstory config`

Manage TermStory configuration and AI provider settings.

```bash
termstory config list         # list all configuration values
termstory config set active_provider ollama
termstory config set providers.groq.api_key "your-key"
termstory config get ai_enabled
```

### Date Override

Query any date:

```bash
termstory 2026-05-15              # summary for May 15th
termstory --date 2026-05-15 week  # week containing May 15th
```

---

## How It Works

```
Shell History Files (zsh/bash)
        ↓
    Parser (parser.py)
        ↓
    Session Grouping (session.py)     — 30-minute gap threshold
        ↓
    Project Detection (project.py)    — VCS roots, config files
        ↓
    Git Commit Ingestion (git_integration.py)  — last 90 days
        ↓
    SQLite Cache (database.py)        — ~/.termstory/termstory.db
        ↓
    AI Sanitizer (sanitizer.py)       — drops passwords, IPs, auth tokens
        ↓
    Memory Extraction (formatter.py / ai.py)
        ↓
    Rich Terminal Output / Interactive TUI (cli.py / tui.py)
```

---

## Architecture

| Module | Purpose |
|---|---|
| `config.py` | Configuration manager, provider setup, path resolution |
| `parser.py` | Parse zsh/bash history files into command records |
| `session.py` | Group commands into sessions by time gaps |
| `project.py` | Detect project roots, humanize names, disambiguate |
| `git_integration.py` | Fetch and clean Git commits via subprocess |
| `database.py` | SQLite storage with WAL mode, timestamp indices, AI caches |
| `sanitizer.py` | Redact sensitive command arguments and drop authentication vectors |
| `ai.py` | Zero-dependency API client, system prompts, few-shot generation |
| `insights.py` | Focus scoring, time-of-day/day-of-week analysis, patterns |
| `formatter.py` | Rich-based terminal rendering, noise filtering, memory heuristics |
| `tui.py` | Interactive asynchronous TUI dashboard built with Textual |
| `cli.py` | Typer CLI, ingestion orchestration, command routing |

---

## Running Tests

```bash
pytest tests/
```

**72 tests** covering parsing, sessions, project detection, git integration, database queries, search, formatting, insights, TUI dashboard features, API networking, and the privacy sanitizer pipeline.

---

## License

MIT
