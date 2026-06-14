import math
import re
import sqlite3
from collections import Counter
from typing import List, Optional, Dict

from termstory.models import Session, Command
from termstory.config import get_db_path
from termstory.ai import _send_llm_request

def _get_project_names_map() -> Dict[int, str]:
    """Helper to extract a mapping of project IDs to names from database."""
    db_path = get_db_path()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM projects;")
        res = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return res
    except Exception:
        return {}

def search_ask(query: str, db) -> List[Session]:
    """
    Search shell history sessions using SQLite FTS5 matching as candidate retrieval,
    then ranks them using a pure-Python TF-IDF scorer.
    
    If FTS5 is not enabled or fails, it falls back to a query with OR'ed LIKE clauses.
    """
    if not query.strip():
        return []

    words = re.findall(r'\w+', query.lower())
    if not words:
        return []

    # 1. Candidate Retrieval
    conn = db.get_connection()
    session_ids = []
    try:
        cursor = conn.cursor()
        
        # Build prefix queries matching FTS5 style, e.g. '"word"*'
        sanitized_terms = []
        for w in words:
            escaped_w = w.replace('"', '""')
            sanitized_terms.append(f'"{escaped_w}"*')
        fts_query = " OR ".join(sanitized_terms)
        
        # Build SQL that joins sessions matching commands, commits, or AI summaries via FTS5
        sql = """
            WITH fts_matches AS (
                SELECT type, ref_id, project_id, timestamp
                FROM search_index
                WHERE search_index MATCH ?
            )
            SELECT DISTINCT s.id
            FROM sessions s
            LEFT JOIN projects p ON s.project_id = p.id
            LEFT JOIN fts_matches f ON (
                (f.type = 'session_summary' AND CAST(f.ref_id AS INTEGER) = s.id)
                OR (f.type = 'command' AND CAST(f.ref_id AS INTEGER) = s.id)
                OR (f.type = 'commit' AND s.project_id = CAST(f.project_id AS INTEGER) 
                    AND CAST(f.timestamp AS INTEGER) >= s.start_time - 300 
                    AND CAST(f.timestamp AS INTEGER) <= s.end_time + 600)
            )
            WHERE (f.ref_id IS NOT NULL)
        """
        # Also allow matching project name in the query words
        project_clauses = []
        project_params = []
        for w in words:
            project_clauses.append("p.name LIKE ?")
            project_params.append(f"%{w}%")
        
        if project_clauses:
            sql += f" OR ( {' OR '.join(project_clauses)} )"
            
        params = [fts_query] + project_params
        
        cursor.execute(sql, params)
        session_ids = [row[0] for row in cursor.fetchall()]
        
    except sqlite3.OperationalError:
        # Fallback to standard LIKE OR search
        try:
            cursor = conn.cursor()
            where_clauses = []
            params = []
            for w in words:
                term_like = f"%{w}%"
                where_clauses.append("(p.name LIKE ? OR c.command LIKE ? OR co.message LIKE ? OR co.cleaned_message LIKE ? OR s.ai_summary LIKE ?)")
                params.extend([term_like, term_like, term_like, term_like, term_like])
            
            sql = f"""
                SELECT DISTINCT s.id
                FROM sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                LEFT JOIN commands c ON s.id = c.session_id
                LEFT JOIN commits co ON s.project_id = co.project_id 
                    AND co.timestamp >= s.start_time - 300 
                    AND co.timestamp <= s.end_time + 600
                WHERE {" OR ".join(where_clauses)}
            """
            cursor.execute(sql, params)
            session_ids = [row[0] for row in cursor.fetchall()]
        except Exception:
            session_ids = []
    finally:
        conn.close()

    if not session_ids:
        return []

    # 2. Retrieve actual Session objects (includes commands, commits)
    sessions = db.get_sessions_by_ids(session_ids)
    if not sessions:
        return []

    project_map = _get_project_names_map()

    # 3. TF-IDF Ranking (pure Python using Counter, math.log, re)
    # Tokenize each session's content
    docs_tokens = []
    for s in sessions:
        doc_parts = []
        p_name = project_map.get(s.project_id, "Other") if s.project_id else "Other"
        doc_parts.append(p_name)
        if s.ai_summary:
            doc_parts.append(s.ai_summary)
        for cmd in s.commands:
            doc_parts.append(cmd.command)
        for commit in s.commits:
            doc_parts.append(commit.get("message", ""))
            doc_parts.append(commit.get("cleaned_message", ""))
        doc_text = " ".join(doc_parts)
        docs_tokens.append(re.findall(r'\w+', doc_text.lower()))

    N = len(sessions)
    
    # Calculate Document Frequency (DF) for each query token (matching prefixes)
    df = {}
    for q_t in words:
        count = 0
        for doc_toks in docs_tokens:
            if any(tok.startswith(q_t) for tok in doc_toks):
                count += 1
        df[q_t] = count

    # Calculate Inverse Document Frequency (IDF) for each query token
    idf = {}
    for q_t in words:
        token_df = df[q_t]
        idf[q_t] = math.log((N + 1) / (token_df + 1)) + 1

    # Calculate TF-IDF Score for each session
    scored_sessions = []
    for idx, s in enumerate(sessions):
        doc_toks = docs_tokens[idx]
        doc_len = len(doc_toks)
        
        score = 0.0
        for q_t in words:
            # TF matching prefix of document tokens
            tf_count = sum(1 for tok in doc_toks if tok.startswith(q_t))
            tf = tf_count / doc_len if doc_len > 0 else 0.0
            score += tf * idf[q_t]
            
        scored_sessions.append((score, s))

    # Sort descending by score, and sub-sort by session start_time descending (most recent first)
    scored_sessions.sort(key=lambda x: (x[0], x[1].start_time), reverse=True)
    
    return [s for _, s in scored_sessions]


def generate_answer(query: str, sessions: List[Session], ai_client) -> Optional[str]:
    """
    Constructs a contextual Q&A prompt using the given query and matched sessions,
    and runs it against the configured LLM client.
    """
    if not query.strip():
        return "Please provide a valid query."
        
    if not sessions:
        return "I could not find any sessions matching your query in the shell history."

    # Extract credentials and provider settings from ai_client
    api_key = ""
    api_base_url = ""
    model_name = ""
    provider = "disabled"
    
    if isinstance(ai_client, dict):
        provider = ai_client.get("provider") or ai_client.get("active_provider") or "disabled"
        providers = ai_client.get("providers", {})
        if provider in providers:
            api_key = providers[provider].get("api_key") or ""
            api_base_url = providers[provider].get("api_base_url") or ""
            model_name = providers[provider].get("model_name") or ""
        else:
            api_key = ai_client.get("api_key") or ""
            api_base_url = ai_client.get("api_base_url") or ""
            model_name = ai_client.get("model_name") or ""
    else:
        provider = getattr(ai_client, "provider", None) or getattr(ai_client, "active_provider", "disabled")
        providers = getattr(ai_client, "providers", None)
        if isinstance(providers, dict) and provider in providers:
            api_key = providers[provider].get("api_key") or ""
            api_base_url = providers[provider].get("api_base_url") or ""
            model_name = providers[provider].get("model_name") or ""
        else:
            api_key = getattr(ai_client, "api_key", "")
            api_base_url = getattr(ai_client, "api_base_url", "")
            model_name = getattr(ai_client, "model_name", "")

    if provider == "disabled" or not provider:
        return "AI capabilities are currently disabled."

    # Fetch project names map
    project_map = _get_project_names_map()

    # Format the session contexts into a technical audit block
    context_blocks = []
    for idx, s in enumerate(sessions):
        p_name = project_map.get(s.project_id, "Other") if s.project_id else "Other"
        
        block = [
            f"Session #{idx + 1}",
            f"Date: {s.date_str} ({s.start_time_formatted}, Duration: {s.duration_readable})",
            f"Project: {p_name}"
        ]
        
        if s.ai_summary:
            block.append(f"Summary: {s.ai_summary.strip()}")
            
        if s.commands:
            block.append("Commands:")
            # Limit command count to avoid context blowout
            for cmd in s.commands[:40]:
                block.append(f"  - {cmd.command}")
            if len(s.commands) > 40:
                block.append(f"  - ... ({len(s.commands) - 40} more commands)")
                
        if s.commits:
            block.append("Git Commits:")
            for commit in s.commits[:15]:
                msg = commit.get("cleaned_message") or commit.get("message") or ""
                if msg.strip():
                    block.append(f"  - {msg.strip()}")
                    
        context_blocks.append("\n".join(block))

    context_text = "\n\n=========================================\n\n".join(context_blocks)

    # Build prompt
    prompt = (
        "You are TermStory Q&A Assistant, an AI helper that answers queries about the user's shell history and development activity.\n"
        "You are given a query and a set of matched shell sessions containing commands, git commits, and session summaries.\n\n"
        "Here is the context of matched sessions:\n"
        "-----------------------------------------\n"
        f"{context_text}\n"
        "-----------------------------------------\n\n"
        f"User Query: {query}\n\n"
        "INSTRUCTIONS:\n"
        "1. Answer the user's query as accurately and concisely as possible using ONLY the provided context.\n"
        "2. If the context does not contain the answer, say so clearly (e.g. 'I could not find information matching your query in the history.').\n"
        "3. Provide relevant command examples, project names, or commit messages when applicable.\n"
        "4. Be technical, developer-friendly, and avoid unnecessary filler or fluff.\n\n"
        "Answer:"
    )

    # Run request using ai._send_llm_request
    result = _send_llm_request(
        prompt=prompt,
        api_key=api_key,
        api_base_url=api_base_url,
        model_name=model_name,
        provider=provider,
        max_tokens=1500,
        timeout=30.0
    )
    return result
