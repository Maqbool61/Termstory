# Directory Context: termstory/

This is the primary application source code directory. It contains all the core Python modules for the `termstory` application, which operates as a personal developer memory engine.

## Core Modules Overview
- `__main__.py` & `cli.py`: Entry point and Command-Line Interface. Handles parsing arguments and executing core commands (e.g., search, today, project, ui).
- `tui.py`: Terminal User Interface built with Textual. Provides an interactive dashboard and timeline view.
- `parser.py`: Parses Zsh and Bash histories, safely extracting timestamps and clean command strings.
- `session.py`: Chains chronological commands into structured work sessions.
- `project.py`: Maps directories to logical project names through VCS root detection and configuration inspection.
- `git_integration.py`: Correlates shell activity with local Git commits.
- `database.py`: Manages SQLite storage in WAL mode, handling schemas, indexing, caching, and deadlocks.
- `ai.py`: Zero-dependency AI client using Python's native `urllib.request` to interface with local or remote LLMs.
- `sanitizer.py`: Redacts sensitive parameters, credentials, and IP addresses before AI summarization.
- `formatter.py`: Helper functions for rich console outputs and formatting results.
- `insights.py`: Aggregates project highlights, telemetry, and achievements.
- `timestamp_detective.py`: An advanced fallback module for interpolating timestamps when standard shell history timestamps are missing.
- `date_utils.py` & `models.py`: Helper utilities and dataclasses for structured data passing.
- `config.py`: Manages AI and general tool configurations.
