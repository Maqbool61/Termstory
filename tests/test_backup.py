import os
import pytest
from termstory.backup import backup_db, restore_db
from termstory.database import Database
from termstory.models import Project, Session, Command

@pytest.fixture
def db_path(tmp_path, monkeypatch):
    db_file = tmp_path / "test_backup.db"
    # Patch the environment variable and functions to ensure they return our temporary database path
    monkeypatch.setenv("DB_PATH", str(db_file))
    monkeypatch.setattr("termstory.config.get_db_path", lambda: str(db_file))
    monkeypatch.setattr("termstory.backup.get_db_path", lambda: str(db_file))
    return str(db_file)

def test_backup_and_restore(db_path, monkeypatch):
    # Initialize database and insert sample data
    db = Database(db_path)
    db.init_db()
    now = 1730000000  # arbitrary timestamp
    project = Project(id=1, name="Demo Project", path="~/demo", first_seen=now, last_seen=now, session_count=1, total_time=100)
    command = Command(timestamp=now, command="echo hello", session_id=1, project_id=1)
    session = Session(id=1, start_time=now, end_time=now + 100, duration_seconds=100, project_id=1, commands=[command])
    db.save_data([project], [session], [command])

    # Perform backup
    backup_path = backup_db()
    assert os.path.isfile(backup_path), "Backup file was not created"

    # Corrupt original db by removing it
    os.remove(db_path)
    assert not os.path.exists(db_path)

    # Restore from backup
    restore_db(backup_path)
    assert os.path.isfile(db_path), "Database file was not recreated after restore"

    # Verify data was restored correctly
    restored_db = Database(db_path)
    restored_db.init_db()
    projects = restored_db.search_projects("")
    assert len(projects) == 1
    assert projects[0].name == "Demo Project"
    
    sessions = restored_db.search_sessions("")
    assert len(sessions) == 1
    assert sessions[0]["duration_seconds"] == 100

    conn = restored_db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT command FROM commands")
    commands = cursor.fetchall()
    conn.close()
    assert len(commands) == 1
    assert commands[0][0] == "echo hello"
