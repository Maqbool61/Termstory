## Summary
Resolves several critical bugs reported in the onboarding and configuration lifecycle of TermStory.

## Changes Made
1. **.zshrc Idempotency:** The CLI onboarding step now checks for existing `EXTENDED_HISTORY` or `HISTTIMEFORMAT` configurations in `~/.zshrc` (or `~/.bashrc`) before attempting to inject them, preventing duplicate lines from being appended across multiple runs or resets.
2. **Reset Cleanup:** When the user runs `termstory reset`, the `perform_reset()` function now executes a safe cleanup routine that removes TermStory's tracking injection blocks from `~/.zshrc` and `~/.bashrc`. User configurations outside the marked blocks are preserved.
3. **API Key Validation:** In the TUI onboarding screen, attempting to save with a blank API key for any cloud provider (Groq, OpenAI, Custom) now shows an inline red error label ("API Key cannot be empty") and prevents the modal from dismissing. `ollama` correctly bypasses this requirement.

## Verification
- Added `test_cli_zshrc_idempotency`
- Added `test_cli_reset_cleanup_rc_files` 
- Added `test_tui_api_key_validation`
- 188/188 unit tests passing successfully.
