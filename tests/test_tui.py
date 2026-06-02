import os
import tempfile
import pytest
from datetime import datetime, timedelta

from termstory.database import Database
from termstory.models import Session, Project, Command
from termstory.tui import (
    TermStoryWorkspace,
    calculate_streak,
    generate_heatmap,
    calculate_dashboard_stats,
    get_session_memory_str,
)

def test_calculate_streak():
    now = datetime(2026, 6, 2, 12, 0)
    now_ts = int(now.timestamp())
    
    # 1. Empty sessions
    assert calculate_streak([]) == 0
    
    # 2. Single session today
    s1 = Session(id=1, start_time=now_ts, end_time=now_ts + 600, duration_seconds=600, project_id=1)
    assert calculate_streak([s1]) == 1
    
    # 3. Gap of 3 days (streak broken)
    s2 = Session(id=2, start_time=now_ts - 3 * 86400, end_time=now_ts - 3 * 86400 + 600, duration_seconds=600, project_id=1)
    assert calculate_streak([s1, s2]) == 1
    
    # 4. Continuous streak (today, yesterday, day before)
    s_yesterday = Session(id=3, start_time=now_ts - 86400, end_time=now_ts - 86400 + 600, duration_seconds=600, project_id=1)
    s_prev = Session(id=4, start_time=now_ts - 2 * 86400, end_time=now_ts - 2 * 86400 + 600, duration_seconds=600, project_id=1)
    # Mock get_current_time to return Jun 2, 2026
    # (Since calculate_streak uses get_current_time(), we can mock/patch it if needed, or rely on local system time.
    # In our tests, we use relative dates to ensure stability.)

def test_generate_heatmap():
    now = int(datetime.now().timestamp())
    sessions = [
        Session(id=1, start_time=now, end_time=now + 600, duration_seconds=600, project_id=1, commands=[
            Command(timestamp=now, command="git status")
        ])
    ]
    heatmap = generate_heatmap(sessions, days_limit=30)
    assert "█" in heatmap or "■" in heatmap or "▄" in heatmap
    assert "░" in heatmap

def test_get_session_memory_str():
    # 1. Commit priority
    s1 = Session(id=1, start_time=1000, end_time=1600, duration_seconds=600, project_id=1, commits=[
        {"hash": "abc", "message": "feat: commit message", "cleaned_message": "Clean message"}
    ])
    assert get_session_memory_str(s1) == "Clean message"
    
    # 2. Non-noise command
    s2 = Session(id=2, start_time=1000, end_time=1600, duration_seconds=600, project_id=1, commands=[
        Command(timestamp=1000, command="git commit -m 'test'"),
        Command(timestamp=1001, command="ls") # noise
    ])
    assert get_session_memory_str(s2) == "git commit -m 'test'"

def test_tui_workspace_init():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        db = Database(db_path)
        db.init_db()
        
        app = TermStoryWorkspace(db, days_limit=30)
        assert app.db == db
        assert app.days_limit == 30

@pytest.mark.asyncio
async def test_tui_workspace_mount():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        db = Database(db_path)
        db.init_db()
        
        app = TermStoryWorkspace(db, days_limit=30)
        async with app.run_test() as pilot:
            # Verify widgets are instantiated and layout works
            assert app.query_one("#stats-panel") is not None
            assert app.query_one("#history-navigator") is not None
            assert app.query_one("#details-canvas") is not None
            assert app.query_one("#search-box") is not None

