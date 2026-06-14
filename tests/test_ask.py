import json
import urllib.request
import urllib.error
import sqlite3
import pytest
from typer.testing import CliRunner
from termstory.cli import app
from termstory.database import Database
from termstory.models import Project, Session, Command
from termstory.ask import search_ask, generate_answer

class MockResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status = status_code
        
    def read(self):
        return self.data
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

def test_search_ask_tfidf_and_ranking(tmp_path):
    db_file = tmp_path / "test_ask_search.db"
    db = Database(str(db_file))
    db.init_db()
    
    now = 1700000000
    
    # Create two projects
    p1 = Project(id=1, name="My Website Project", path="~/web", first_seen=now, last_seen=now, session_count=1, total_time=100)
    p2 = Project(id=2, name="Other CLI", path="~/cli", first_seen=now, last_seen=now, session_count=1, total_time=100)
    
    # Session 1: contains "deploy website" multiple times in commands/summary
    cmd1 = Command(timestamp=now, command="git push origin main", session_id=1, project_id=1)
    cmd2 = Command(timestamp=now + 50, command="npm run deploy", session_id=1, project_id=1)
    s1 = Session(id=1, start_time=now, end_time=now + 100, duration_seconds=100, project_id=1, commands=[cmd1, cmd2])
    s1.ai_summary = "Deploying website build to production"
    
    # Session 2: does not contain "deploy" or "website"
    cmd3 = Command(timestamp=now, command="python3 test.py", session_id=2, project_id=2)
    s2 = Session(id=2, start_time=now, end_time=now + 100, duration_seconds=100, project_id=2, commands=[cmd3])
    s2.ai_summary = "Running python test cases"
    
    db.save_data([p1, p2], [s1, s2], [cmd1, cmd2, cmd3])
    db.save_session_ai_summary(1, s1.ai_summary)
    db.save_session_ai_summary(2, s2.ai_summary)
    
    # Perform search_ask for "deploy"
    results = search_ask("deploy", db)
    assert len(results) >= 1
    assert results[0].id == 1  # Session 1 has "deploy" and should be ranked first
    
    # Perform search_ask for "website"
    results = search_ask("website", db)
    assert len(results) >= 1
    assert results[0].id == 1

def test_search_ask_project_name_matching(tmp_path):
    db_file = tmp_path / "test_ask_proj.db"
    db = Database(str(db_file))
    db.init_db()
    
    now = 1700000000
    p = Project(id=1, name="SpecialSecretProject", path="~/secret", first_seen=now, last_seen=now, session_count=1, total_time=100)
    cmd = Command(timestamp=now, command="ls", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 100, duration_seconds=100, project_id=1, commands=[cmd])
    db.save_data([p], [s], [cmd])
    
    # search_ask matches project name words
    results = search_ask("SpecialSecretProject", db)
    assert len(results) == 1
    assert results[0].id == 1

def test_search_ask_fts5_fallback(tmp_path, monkeypatch):
    db_file = tmp_path / "test_ask_fallback.db"
    db = Database(str(db_file))
    db.init_db()
    
    now = 1700000000
    p = Project(id=1, name="Fallback Test Project", path="~/fallback", first_seen=now, last_seen=now, session_count=1, total_time=100)
    cmd = Command(timestamp=now, command="docker-compose up -d", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 100, duration_seconds=100, project_id=1, commands=[cmd])
    db.save_data([p], [s], [cmd])
    
    original_get_connection = db.get_connection
    def get_broken_connection():
        conn = original_get_connection()
        original_cursor = conn.cursor
        def broken_cursor(*args, **kwargs):
            cursor = original_cursor(*args, **kwargs)
            original_execute = cursor.execute
            def broken_execute(sql, *exec_args):
                if "MATCH" in sql:
                    raise sqlite3.OperationalError("Mocked FTS5 error")
                return original_execute(sql, *exec_args)
            cursor.execute = broken_execute
            return cursor
        conn.cursor = broken_cursor
        return conn
        
    monkeypatch.setattr(db, "get_connection", get_broken_connection)
    
    # search_ask should fall back to standard LIKE OR search and still retrieve the session
    results = search_ask("docker-compose", db)
    assert len(results) == 1
    assert results[0].id == 1

def test_generate_answer_disabled():
    # Test generate_answer when provider is disabled
    sessions = [Session(id=1, start_time=1700000000, end_time=1700000100, duration_seconds=100, project_id=1)]
    ai_client = {"active_provider": "disabled"}
    res = generate_answer("What did I do?", sessions, ai_client)
    assert res == "AI capabilities are currently disabled."

def test_generate_answer_success(monkeypatch):
    called = []
    
    def mock_urlopen(req, timeout=None):
        called.append(req)
        resp_payload = {
            "choices": [
                {
                    "message": {
                        "content": "You deployed the website project."
                    }
                }
            ]
        }
        return MockResponse(json.dumps(resp_payload).encode("utf-8"))
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    sessions = [
        Session(id=1, start_time=1700000000, end_time=1700000100, duration_seconds=100, project_id=1, commands=[
            Command(timestamp=1700000000, command="npm run deploy", session_id=1, project_id=1)
        ])
    ]
    ai_client = {
        "active_provider": "groq",
        "providers": {
            "groq": {
                "api_key": "test-key",
                "api_base_url": "https://api.groq.com/openai/v1",
                "model_name": "llama3"
            }
        }
    }
    
    res = generate_answer("What did I do?", sessions, ai_client)
    assert len(called) == 1
    assert res == "You deployed the website project."

def test_cli_ask_command(tmp_path, monkeypatch):
    db_file = tmp_path / "test_cli_ask.db"
    config_file = tmp_path / "config.json"
    
    monkeypatch.setattr("termstory.cli.get_db_path", lambda: str(db_file))
    monkeypatch.setattr("termstory.config.get_db_path", lambda: str(db_file))
    monkeypatch.setattr("termstory.config.get_config_path", lambda: str(config_file))
    monkeypatch.setattr("termstory.cli.get_history_files", lambda: [])
    
    db = Database(str(db_file))
    db.init_db()
    
    # Save a session
    now = 1700000000
    p = Project(id=1, name="My Project", path="~/proj", first_seen=now, last_seen=now, session_count=1, total_time=100)
    cmd = Command(timestamp=now, command="git commit -m 'feat: add ask CLI'", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 100, duration_seconds=100, project_id=1, commands=[cmd])
    db.save_data([p], [s], [cmd])
    
    # Write a config file with active provider as groq
    config_data = {
        "active_provider": "groq",
        "providers": {
            "groq": {
                "api_key": "test-key",
                "api_base_url": "https://api.groq.com/openai/v1",
                "model_name": "llama3"
            }
        }
    }
    with open(config_file, "w") as f:
        json.dump(config_data, f)
        
    # Mock LLM API call
    called = []
    def mock_urlopen(req, timeout=None):
        called.append(req)
        resp_payload = {
            "choices": [
                {
                    "message": {
                        "content": "You committed a new feature 'feat: add ask CLI'."
                    }
                }
            ]
        }
        return MockResponse(json.dumps(resp_payload).encode("utf-8"))
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    runner = CliRunner()
    
    # 1. Ask query that matches
    result = runner.invoke(app, ["ask", "ask CLI"])
    assert result.exit_code == 0
    assert "You committed a new feature 'feat: add ask CLI'." in result.stdout
    assert len(called) == 1
    
    # 2. Ask query that doesn't match anything
    result2 = runner.invoke(app, ["ask", "non-existent-word"])
    assert result2.exit_code == 0
    assert "No relevant history found" in result2.stdout
