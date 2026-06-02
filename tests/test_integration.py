import os
import time
from typer.testing import CliRunner
from termstory.cli import app
from termstory.database import Database

def test_cli_today_workflow(tmp_path, monkeypatch):
    # Mock db path and history files
    db_file = tmp_path / "test_termstory.db"
    monkeypatch.setattr("termstory.cli.get_db_path", lambda: str(db_file))
    
    zsh_history_file = tmp_path / "zsh_history"
    now_ts = int(time.time())
    
    # Write sample history for today
    zsh_history_file.write_text(
        f": {now_ts - 3600}:0;git status\n"
        f": {now_ts - 3550}:0;cd ~/projects/incubator-hugegraph\n"
        f": {now_ts - 3500}:0;docker compose up\n"
        f": {now_ts}:0;git commit -m 'Fix integration test'\n"
    )
    
    monkeypatch.setattr("termstory.cli.get_history_files", lambda: [str(zsh_history_file)])
    
    # Run CLI
    runner = CliRunner()
    result = runner.invoke(app, ["today"])
    assert result.exit_code == 0
    assert "Today" in result.stdout
    assert "Apache HugeGraph" in result.stdout
    assert "git commit" in result.stdout.lower()
    assert "docker compose" in result.stdout.lower()
    
    # Check that database has the records populated
    db = Database(str(db_file))
    sessions = db.get_today_sessions()
    assert len(sessions) == 2 # 1 hour gap between now_ts - 3500 and now_ts
    
    # Verify commands count
    total_commands = sum(len(s.commands) for s in sessions)
    assert total_commands == 4
