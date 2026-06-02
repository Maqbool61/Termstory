# TermStory Developer Memory Engine — State & Context (agents.md)

This file maintains the active development state, design philosophy, and progress for TermStory to ensure seamless context transfer across model switches.

---

## 1. Core Philosophy: Developer Memory Engine

TermStory is **not** a dashboard or a reporting tool. It is a **developer memory engine**.
- **Recognize, don't inspect**: Optimize for recognition ("What did I work on?"). Details ("How do you know?") belong in `--detailed` mode.
- **Density over decoration**: No rounded panels, double borders, or nested boxes. Use clean column alignment, simple tables, and minimal spacing.
- **Screenshot-friendly**: Every screen should fit in a single terminal screen/screenshot and tell a compelling story about a developer's day, search, or project.
- **Map General to Other**: "General / No Project" or empty project names are mapped to `"Other"`.
- **Noise Filtering**: Filter out routine navigation, status, and inspection commands (like `cd`, `ls`, `docker ps`, `git status`, `docker logs`, `grep`, etc.) so only creative/memorable work remains.

---

## 2. Command Redesign Status

### 🔍 `termstory search` (COMPLETED & PUSHED)
- **Status**: Implemented, tested, and pushed.
- **Features**: Groups by project, collapses multiple daily sessions into a single line per day, prioritizes commits over commands, filters noise commands, and maps General to Other.
- **Files**: Edited `format_search_results` and added helper methods `_is_noise_command`, `_get_session_memory`, `_collapse_by_day` in [formatter.py](file:///Users/himanshuverma/Projects/termstory/termstory/formatter.py).

### 📋 `termstory today` (COMPLETED & PUSHED)
- **Status**: Implemented, tested, and pushed.
- **Features**: Clean bulleted timeline per project with project-level duration summaries, yesterday comparison support, and noise filtering.
- **Files**: Edited `format_today_output` in [formatter.py](file:///Users/himanshuverma/Projects/termstory/termstory/formatter.py).

### 📁 `termstory project` (COMPLETED & PUSHED)
- **Status**: Implemented, tested, and pushed.
- **Features**: Replaced cards with a clean, high-density, box-free list of dates and milestone accomplishments/memories per day.
- **Files**: Edited `format_project_output` in [formatter.py](file:///Users/himanshuverma/Projects/termstory/termstory/formatter.py).

### 💡 `termstory insights` / Highlights (COMPLETED & PUSHED)
- **Status**: Implemented, tested, and pushed.
- **Features**: Completely overhauled cards, empty charts, and focus score metrics into a compact, clean executive highlights list showing project active days, total duration, and main achievements.
- **Files**: Edited `format_insights_output` and `_get_project_main_achievement` in [formatter.py](file:///Users/himanshuverma/Projects/termstory/termstory/formatter.py).

---

## 3. Running Verification

Always verify changes using:
```bash
python3 -m pytest tests/
```
And manually inspect outputs via:
```bash
python3 -m termstory.cli today
python3 -m termstory.cli project termstory
python3 -m termstory.cli insights
```
