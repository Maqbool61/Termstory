# Directory Context: tests/

This directory contains the comprehensive test suite for the `termstory` application, using `pytest`.

## Key Test Categories
- **Core Unit Tests**: `test_ai.py`, `test_parser.py`, `test_database.py`, `test_database_queries.py`, `test_session.py`, `test_project.py`, `test_sanitizer.py`, `test_git_integration.py`
- **TUI & CLI Tests**: `test_tui.py`, `test_cli_commands.py`, `test_formatter_rich.py`
- **Advanced / Expert Validations**: Concurrency and memory tests to ensure thread safety (`test_expert_concurrency.py`, `test_expert_thread_starvation.py`, `test_expert_memory_leak.py`, `test_expert_resize.py`).
- **Edge Cases & Specific Scenarios**: `test_ai_error_surfacing.py`, `test_timestamp_detective.py` (for legacy time interpolation engine).

## Fixtures
The `fixtures/` subdirectory provides mock histories, templates, and text examples used by the test modules to run reliably without mutating actual user data.
