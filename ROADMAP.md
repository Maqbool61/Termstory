# TermStory Future Roadmap & Vision

This document tracks long-term, transformational concepts for TermStory aligned with our "Developer Memory Engine" philosophy. Immediate technical milestones live in `agents.md`.

---

## v0.4.x — In Progress

- **SQLite FTS5 Integration**: Full-Text Search across sessions, commands, and AI summaries for ranked, sub-millisecond matching.
- **Concurrency Stress Tests & Massive History Simulations**: Multi-year synthetic history logs to harden ingestion race-condition coverage.
- **Project-Specific AI Contexts**: Seed LLM prompts with per-project context descriptors for richer, more accurate narratives.
- **`agy` Subcommand**: One-shot `termstory agy` to launch `agy -p` for quick AI pair-programming sessions bridged from shell history.
- **Pre-Cognitive Workspace** (`termstory predict`): Pattern-based session analysis that predicts what a developer will work on next. Surfaces recency momentum, time-of-day affinity, day-of-week cadence, and interrupted session detection. Implemented in `predict.py` with full test coverage.
- **"Ghost-in-the-Shell" TUI Playback**: Visual, step-by-step terminal playback of selected sessions (`termstory replay`) in fast/slow motion.

---

## v0.5.x — Planned

- **GitHub Actions CI Pipeline**: Automated `pytest` + lint gate on every PR via `.github/workflows/ci.yml`.
- **PyPI automated release workflow**: Tag-triggered build and publish pipeline.
- **`termstory profile` command**: CLI profiler surfacing slowest DB queries and top N+1 read patterns from live ingestion.

---

## Longer-Term Research

## 1. "REM Sleep" Context Consolidation
**Concept**: Overnight meta-pattern fusing.
**Details**: Much like human REM sleep processes and consolidates the day's memories, TermStory could leverage idle, overnight periods to run heavy AI meta-analysis on recent sessions. This would identify high-level behavioral patterns, extract persistent learning goals, and compress redundant steps into profound, overarching behavioral insights without blocking daily tasks.

## 2. MCP (Model Context Protocol) Time-Machine Snapshots
**Concept**: Semantic snapshots of external tools.
**Details**: By integrating with the Model Context Protocol, TermStory could capture synchronized snapshots of a developer's external ecosystem (e.g., active browser tabs, IDE state, ticket status) alongside CLI commands. This "time-machine" capability would preserve full context loops and provide historically accurate replays of what the overall workspace looked like during specific sessions.

## 3. Pre-Cognitive Workspace (Branch Prediction for Devs)
**Concept**: E.g., Friday context loaded on Monday.
**Details**: Using historical session chains and contextual momentum, TermStory predicts what a developer will likely work on next. For instance, if a developer pauses an intense debugging session on Friday evening, the Pre-Cognitive Workspace could preemptively stage summaries, fetch relevant git diffs, and suggest the most likely next commands automatically on Monday morning.

## 4. Semantic Deep-Dive via Local RAG
**Concept**: Zero-Keyword Search using local embeddings.
**Details**: Transitioning beyond SQLite FTS, this involves creating a lightweight, local Retrieval-Augmented Generation (RAG) pipeline. By generating embeddings for shell sessions and commit narratives natively, TermStory could facilitate "Zero-Keyword" semantic searching. Developers could query abstract concepts like "that time I fixed the database deadlock" and be routed to the exact session, even if they can't remember any specific commands.

---
*Maintained in adherence to TermStory's "density over decoration" ethos. No unnecessary elements, just a clear blueprint of the future.*
