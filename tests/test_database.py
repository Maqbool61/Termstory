import time
from termstory.database import Database
from termstory.models import Command, Session, Project

def test_init_db(tmp_path):
    db_file = tmp_path / "test_init.db"
    db = Database(str(db_file))
    db.init_db()
    
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "projects" in tables
    assert "sessions" in tables
    assert "commands" in tables
    conn.close()

def test_insert_and_retrieve(tmp_path):
    db_file = tmp_path / "test_data.db"
    db = Database(str(db_file))
    db.init_db()
    
    # Use current epoch time to ensure retrieved records fall under "today" query window
    now_ts = int(time.time())
    
    # 1. Create memory entities with temporary sequential IDs
    project = Project(
        id=99, # Temp python ID
        name="Apache HugeGraph",
        path="~/projects/incubator-hugegraph",
        first_seen=now_ts,
        last_seen=now_ts + 100,
        session_count=1,
        total_time=100
    )
    cmd = Command(
        timestamp=now_ts,
        command="git status",
        exit_code=0,
        session_id=1,
        project_id=99
    )
    session = Session(
        id=999, # Temp python ID
        start_time=now_ts,
        end_time=now_ts + 100,
        duration_seconds=100,
        project_id=99,
        commands=[cmd]
    )
    
    # 2. Save using the bulk mapping transaction method
    db.save_data([project], [session], [cmd])
    
    # Check that database IDs were mapped back to the python entities
    assert project.id is not None
    assert project.id != 99
    assert session.id is not None
    assert session.id != 999
    assert cmd.project_id == project.id
    assert cmd.session_id == session.id
    
    # 3. Retrieve today's sessions
    today_sessions = db.get_today_sessions()
    assert len(today_sessions) == 1
    
    db_session = today_sessions[0]
    assert db_session.id == session.id
    assert db_session.start_time == now_ts
    assert db_session.project_id == project.id
    
    # 4. Retrieve today's projects
    today_projects = db.get_projects_by_ids([db_session.project_id])
    assert len(today_projects) == 1
    assert today_projects[0].name == "Apache HugeGraph"
    assert today_projects[0].path == "~/projects/incubator-hugegraph"
    
    # 5. Check commands inside session
    assert len(db_session.commands) == 1
    db_cmd = db_session.commands[0]
    assert db_cmd.command == "git status"
    assert db_cmd.session_id == db_session.id
    assert db_cmd.project_id == project.id

def test_session_growth_updates_existing_session(tmp_path):
    db_file = tmp_path / "test_growth.db"
    db = Database(str(db_file))
    db.init_db()
    
    now_ts = int(time.time())
    
    # Session starts with one command
    project = Project(id=1, name="Proj A", path="~/proj-a", first_seen=now_ts, last_seen=now_ts, session_count=1, total_time=0)
    cmd1 = Command(timestamp=now_ts, command="git status", exit_code=0, session_id=1, project_id=1)
    session1 = Session(id=1, start_time=now_ts, end_time=now_ts, duration_seconds=0, project_id=1, commands=[cmd1])
    
    db.save_data([project], [session1], [cmd1])
    db_session_id = session1.id
    
    # Session grows: new command added, end_time changes, duration changes
    cmd2 = Command(timestamp=now_ts + 300, command="git diff", exit_code=0, session_id=1, project_id=1)
    session2 = Session(id=1, start_time=now_ts, end_time=now_ts + 300, duration_seconds=300, project_id=1, commands=[cmd1, cmd2])
    
    db.save_data([project], [session2], [cmd1, cmd2])
    
    # Retrieve sessions and verify only ONE row exists and has the updated duration/end_time
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, start_time, end_time, duration_seconds, project_id FROM sessions")
    rows = cursor.fetchall()
    conn.close()
    
    assert len(rows) == 1
    assert rows[0][0] == db_session_id
    assert rows[0][2] == now_ts + 300 # Updated end_time
    assert rows[0][3] == 300          # Updated duration


def test_macro_summaries_caching(tmp_path):
    db_file = tmp_path / "test_macro.db"
    db = Database(str(db_file))
    db.init_db()
    
    # Verify table exists
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "macro_summaries" in tables
    conn.close()
    
    # Test saving and retrieving
    timeframe_id = "2026-06"
    assert db.get_macro_summary(timeframe_id) is None
    
    db.save_macro_summary(timeframe_id, "month", "Review summary text.")
    assert db.get_macro_summary(timeframe_id) == "Review summary text."
    
    # Test overwriting (UPSERT-like behavior)
    db.save_macro_summary(timeframe_id, "month", "Updated review summary text.")
    assert db.get_macro_summary(timeframe_id) == "Updated review summary text."


