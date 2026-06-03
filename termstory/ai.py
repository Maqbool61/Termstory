import json
import urllib.request
import urllib.error
from typing import List, Optional
from termstory.sanitizer import sanitize_session_commands

def _send_llm_request(
    prompt: str,
    api_key: str,
    api_base_url: str,
    model_name: str,
    provider: str
) -> Optional[str]:
    """Shared helper to construct and send the OpenAI-compatible chat completion request."""
    if provider == "disabled":
        return None
        
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "TermStory/1.0"
    }
    if api_key and isinstance(api_key, str) and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"
        
    # OpenAI compatibility endpoint (normalize trailing slash)
    if not api_base_url or not isinstance(api_base_url, str):
        return None
    endpoint = api_base_url.strip().rstrip('/')
    if not endpoint.endswith('/chat/completions'):
        endpoint = f"{endpoint}/chat/completions"
        
    body = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.0,
        "max_tokens": 150
    }
    
    req_data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(endpoint, data=req_data, headers=headers, method="POST")
    
    try:
        # Set a reasonable timeout for the TUI background thread
        with urllib.request.urlopen(req, timeout=15.0) as response:
            resp_data = response.read().decode("utf-8")
            resp_json = json.loads(resp_data)
            result = resp_json["choices"][0]["message"]["content"].strip()
            # Clean up any quotes added by the LLM
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            if result.startswith("'") and result.endswith("'"):
                result = result[1:-1]
            return result
    except Exception:
        # Gracefully fail and return None
        return None

def generate_ai_summary(
    commands: List[str],
    api_key: str,
    api_base_url: str,
    model_name: str,
    provider: str,
    project_name: str = "Other",
    commits: Optional[List[str]] = None
) -> Optional[str]:
    """Scrub commands and query the configured LLM API (Groq or Ollama) to generate a summary."""
    if not commands:
        return None
        
    # 1. Sanitization Pipeline
    sanitized_cmds, is_blacklisted = sanitize_session_commands(commands)
    if is_blacklisted:
        return "Security/Authentication Operations"
        
    if not sanitized_cmds:
        return None
        
    # If AI provider is disabled, return None (fallback to local heuristics)
    if provider == "disabled":
        return None
        
    # 2. Formulate the prompt
    commands_block = "\n".join(f"- {cmd}" for cmd in sanitized_cmds)
    
    commits_block = ""
    if commits:
        unique_commits = sorted(list(set(commits)))
        commits_block = "\nGit Commit Messages:\n" + "\n".join(f"- {c}" for c in unique_commits)
        
    prompt = (
        "Translate the developer's raw shell commands and Git commits into a high-density, CLI-styled terminal log of their work session.\n\n"
        "YOUR CORE GOAL:\n"
        "Generate a 3-line bulleted dev log. It must resemble a clean, tech-dense terminal audit output using ASCII connection lines or tech symbols.\n\n"
        "Choose ONE of the following formats to return, matching the inputs:\n\n"
        "Format Option A (ASCII branch log style):\n"
        "[💻 Dev Log]\n"
        "├─ 🔨 Built: <short, punchy action phrase of what was built or coded, using tech keywords>\n"
        "├─ 🔧 Flow: <brief sequence of tools used, tests run, or configurations edited>\n"
        "└─ 🚀 Result: <final milestone shipped, fixed, or pushed>\n\n"
        "Format Option B (Tech bullet list style):\n"
        "[🤖 Codebase Pulse]\n"
        "• Hacked: <what was designed, refactored, or debugged>\n"
        "• Tooling: <commands run, docker setups, or libraries configured>\n"
        "• Outcome: <what was successfully verified, resolved, or shipped>\n\n"
        "Choose either Option A or Option B at random or based on the inputs to provide variation, but always output EXACTLY the selected format.\n"
        "Never output any paragraphs of text, conversational filler, markdown formatting, or surrounding quotes. Only return the raw 4 lines of console text.\n\n"
        "STYLE & TONE RULES:\n"
        "1. NO MARKETING FLUFF: Never write paragraphs like 'Ultimately, the hard work paid off...'. Keep it purely developer-centric and density-focused.\n"
        "2. START WITH ACTION VERBS: Each bullet line must start directly with an active, past-tense engineering verb (e.g., 'wired up', 'refactored', 'debugged', 'spun up', 'implemented').\n"
        "3. Keep each line extremely concise, informative, and technical.\n\n"
        "Input Data to Summarize:\n"
        f"Project: {project_name}\n"
        "Commands Executed:\n"
        f"{commands_block}\n"
        f"{commits_block}\n\n"
        "Output format: Return ONLY the raw, polished console text block. No markdown formatting, no conversational filler, and no surrounding quotes."
    )
    
    return _send_llm_request(prompt, api_key, api_base_url, model_name, provider)


def generate_timeframe_summary(
    stats_summary: str,
    api_key: str,
    api_base_url: str,
    model_name: str,
    provider: str
) -> Optional[str]:
    """Query LLM to generate a professional action-oriented summary of a timeframe."""
    if provider == "disabled":
        return None
        
    prompt = (
        "Write a highly-personalized, modern engineering review of the developer's work over this entire period based on their commits, session summaries, and tooling stats.\n\n"
        "YOUR CORE GOAL:\n"
        "Generate a high-density, CLI-styled audit review of the timeframe. It must resemble terminal diagnostic output using ASCII connection lines, matching this exact structure:\n\n"
        "✨ [⚡ Timeframe Audit]\n"
        "├─ 📂 <Project A Name>   [XX%]\n"
        "├─ 📂 <Project B Name>   [XX%]\n"
        "└─ 📂 Misc / Sys Config  [XX%]\n\n"
        "RULES FOR GENERATION:\n"
        "1. Extract the projects and their percentage distributions from the input context (PROJECTS DISTRIBUTION).\n"
        "2. List the projects in descending order of percentage.\n"
        "3. Truncate any projects with less than 5% share or named 'Other', and group their combined percentages into a single final line: '└─ 📂 Misc / Sys Config  [XX%]'.\n"
        "4. Use the branch characters correctly: '├─ 📂' for all projects except the last one, which must use '└─ 📂'.\n"
        "5. Keep the alignment neat.\n"
        "6. Do not output any paragraphs, explanations, conversational filler, markdown formatting, or surrounding quotes. Only return the raw lines of console text.\n\n"
        f"Developer Work Log Context:\n"
        f"{stats_summary}\n\n"
        "Output format: Return ONLY the raw, polished console text block. No markdown formatting, no conversational filler, and no surrounding quotes."
    )
    
    return _send_llm_request(prompt, api_key, api_base_url, model_name, provider)
