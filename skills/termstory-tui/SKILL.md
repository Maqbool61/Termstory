---
name: termstory-tui
description: Design, implement, and debug the Textual-based UI for TermStory, balancing high-density console philosophy with modern reactive rendering.
---

# TermStory TUI Development Guide

Welcome to the TermStory TUI Skill. The TermStory TUI is built using [Textual](https://textual.textualize.io/) and orchestrates the complex visual interaction layer of the developer memory engine. This guide synthesizes extreme structural minimalism (density) with modern, progressive UX capabilities.

## 1. Core Philosophy: Density Over Decoration
Terminal real estate is precious. Every view must optimize for immediate developer recognition without cognitive fatigue or visual clutter.
- **BANNED**: `rich.panel.Panel`, double borders, nested boxes, and bulky padded containers.
- **REQUIRED**: Clean column alignment, simple tables, minimal spacing, and dense text separators (e.g., `├─`, `└─`, `•`).
- **Zero-Margin Layouts**: Eliminate dead space. Use `margin: 0;` and `padding: 0;` by default.
- **Screenshot-Ready**: Every interface state must comfortably fit in a single terminal screen/screenshot and tell a complete narrative.

## 2. Layout & Structure
The primary application dashboard strictly adheres to a fixed proportional layout:
- **30% / 70% Split**: 
  - **Left Pane (30%)**: The `HistoryTree` explorer. Hide the redundant root node (`Timeline Explorer`) via constructor arguments to maximize horizontal space.
  - **Right Pane (70%)**: The `DetailsCanvas` (scrollable narrative, chronicle, and detail area).
- **Header & Footer**: Utilize a `StatsHeader` at the top for activity heatmaps and active streaks. Center keyboard shortcuts in the `Footer`.

## 3. Modern UX & Progressive Disclosure
While maintaining ultra-minimalist structures, leverage modern, GPU-accelerated terminal features to enrich the experience asynchronously.
- **Tooltips over Text**: Use Textual's `tooltip` properties extensively for secondary information (e.g., full paths, timestamps) instead of persistently printing them on screen.
- **Hover & Mouse Awareness**: Terminals are mouse-aware. Implement subtle CSS hover states for interactive elements to guide the user naturally.
- **Smart Collapsibles**: If nested views are unavoidable, use dense `Collapsible` components rather than nested borders to maintain a flat visual hierarchy.
- **Robust Keybinds**: Prioritize a keyboard-first flow (`j/k` navigation, `Enter` to expand, `?` for help, `Esc` to escape scope).
- **OS-Level Copying**: Override standard copy mechanisms to pipe directly to `pbcopy`/`xclip`/`clip`, ensuring shortcut `c` works reliably even without OSC 52 support.

## 4. Concurrency & Asynchronous Safety
Never block the main UI thread. Textual's reactivity depends on the event loop remaining entirely free.
- **Worker Guards**: Offload all database reads, heavy text formatting, and AI API calls using Textual workers: `@work(thread=True, exclusive=True)`. The `exclusive=True` flag is mandatory; it acts as a LIFO-style debounce, preventing thread-pool starvation from rapid arrow-key scrolling.
- **Database Thread-Safety**: Use explicit `BEGIN IMMEDIATE` transactions and `INSERT OR IGNORE` in all concurrent background database operations to eliminate SQLite Upgrade Deadlocks.
- **Loading Indicators**: Provide clear visual feedback for asynchronous operations using Textual's native `LoadingIndicator` instead of modal popups. Set a secondary wall-clock timeout circuit breaker for all AI operations.

## 5. Development & Debugging Workflow
Standard `print()` statements will corrupt the TUI. Debugging must be performed through Textual's native developer tools.
- **Dev Mode Execution**: Start the application in development mode to enable CSS hot-reloading:
  ```bash
  textual run --dev termstory.cli ui
  ```
- **Console Monitoring**: In a separate terminal tab, monitor logs, events, and exceptions:
  ```bash
  textual console
  ```
- **Application Logging**: Always use Textual's logging facility: `from textual import log; log("Debug context")`.

## 6. Empty States & Graceful Degradation
- **Zero-Session Guard**: If a user launches the UI with an empty database, do not crash or render an empty canvas. Display a welcoming, screenshot-friendly troubleshooting and permission guide inside the `DetailsCanvas`.
- **Action Blocking**: Preemptively guard and disable AI summary actions when `0` sessions are detected.
