# How TermStory Handles Your Data (Trust Architecture)

Terminal history is the most sensitive data on your machine. TermStory was built on a singular principle: **Your data belongs to you, and it never leaves your machine without your explicit consent.**

This document outlines exactly how TermStory processes your history, how our optional AI features work, and the strict sanitization measures we take to protect your secrets.

### 1. Default State: 100% Offline

Out of the box, TermStory is completely offline. The CLI parses your local `.zsh_history` or `.bash_history` files, stores the data in a local SQLite database (`~/.termstory/db.sqlite`), and renders the UI locally. No telemetry is collected, and no network requests are made.

### 2. The Optional AI Engine

To make your timeline read like a true work diary, TermStory offers an **opt-in** AI categorization engine. When enabled, TermStory sends small batches of your terminal commands and git commit messages to an LLM (like Groq) to generate a short, human-readable summary of what you were working on.

Three features send data to the LLM when enabled: **auto-summaries** (background, per session), the **Daily Chronicle** (`termstory chronicle`), and **natural language queries** (`termstory ask`). All three pass your history through the Local Sanitization Engine before making any network request.

**If you enable this feature, we do not just blindly send your terminal logs to the cloud.** Your data must pass through our Local Sanitization Engine first.

### 3. The Local Sanitization Engine

Before a single byte of data is sent to the AI API, TermStory runs your session commands and git commit messages through a rigid Python pre-processor right on your laptop.

#### Open-Source Secret Detection

We do not reinvent the wheel when it comes to security. TermStory's redaction engine utilizes patterns from **Secrets-Patterns-DB**.

* This is an open-source database containing over 1,600 community-vetted regular expressions designed to detect passwords, API keys, and cloud tokens.
* If a command matches any of these 1,600+ patterns, the sensitive string is immediately stripped and replaced with `[REDACTED]` before leaving your machine.

#### Blacklisted Workflows

If a session contains commands associated with deep infrastructure management or secret vaulting, TermStory removes that session's raw command list from the LLM context entirely and replaces it with `[REDACTED: Security/Authentication Operations]`. Session metadata (date, project name, duration, cached AI summaries) remains visible — only raw command text is withheld. We will never send raw commands from sessions containing patterns like:

* `vault *`
* `aws configure`
* `gh auth`
* `kubectl create secret *`
* Raw token strings: `github_pat_*`, `sk_live_*`, `sk-ant-*`, `npm_*` (36-char)

#### Hardcoded Redactions

Even if a command passes the Regex database, we aggressively strip common vectors for accidental secret leakage:

* Everything following an equals sign in environment variables (e.g., `export DB_PASS=[REDACTED]`).
* Everything following common password flags (e.g., `mysql -u root -p[REDACTED]`).
* IP addresses and fully qualified domain names (FQDNs).

#### Custom Redaction Rules (`.termstoryignore`)

If your workflows produce secrets with no recognizable prefix (e.g., a company-internal token format), you can teach TermStory's sanitizer about them without modifying source code.

Place additional regex patterns — one per line — in either of these files:
* `~/.termstoryignore`
* `~/.termstory/.termstoryignore`

Lines starting with `#` are treated as comments. Patterns match case-insensitively; matched strings are replaced with `[REDACTED_CUSTOM]`.

**Example `~/.termstoryignore`:**
```
# Redact internal Vault paths
secret/data/.*

# Redact custom internal API token format
acme_tok_[a-z0-9]{32}
```

> **Note:** Custom patterns are loaded once at TermStory startup. If you edit `.termstoryignore` while TermStory is running, restart it to apply the changes.

### 4. Run It Entirely Offline (Ollama Support)

If you want the beautiful AI-generated summaries but are strictly prohibited from sending sanitized logs to a cloud provider like Groq, TermStory supports local LLMs natively.

Simply install [Ollama](https://ollama.com/), pull a model like `llama3`, and point TermStory to your local instance in the configuration. TermStory will generate your work diary locally, guaranteeing absolute data privacy.

### 5. Pro-Tip: The Native Shell Bypass

If you are typing a command that you know contains a plaintext secret and you don't even want it logged to TermStory's local SQLite database, utilize your shell's native ignore feature:

* Ensure `HISTCONTROL=ignorespace` is set in your `.zshrc` or `.bashrc`.
* **Type a space before your command** (e.g., ` docker login -u root -p password`).
* The shell will refuse to write it to your history file, meaning TermStory will never see it.
