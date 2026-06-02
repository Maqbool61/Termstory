import time
from datetime import datetime
from termstory.models import Project, Session, Command
from termstory.formatter import (
    format_today_output,
    format_week_output,
    format_month_output,
    format_project_output,
    format_projects_list,
    format_detailed_sessions,
    format_search_results,
    format_insights_output,
    make_visual_bar
)

def test_make_visual_bar():
    # Test complete bar
    bar = make_visual_bar(10, 10, width=10)
    assert "█" in bar
    assert "░" not in bar
    
    # Test empty bar
    bar = make_visual_bar(0, 10, width=10)
    assert "░" in bar
    assert "█" not in bar

def test_formatter_today_output():
    now = int(time.time())
    p = Project(id=1, name="Project Delta", path="~/delta", first_seen=now, last_seen=now, session_count=1, total_time=600)
    cmd = Command(timestamp=now, command="git diff", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 600, duration_seconds=600, project_id=1, commands=[cmd], commits=[
        {"hash": "abcdefabcdef", "timestamp": now, "message": "feat: init", "cleaned_message": "Init"}
    ])
    
    output = format_today_output([s], [p])
    assert "Project Delta" in output
    assert "Init" in output

def test_formatter_week_output():
    now = int(time.time())
    p = Project(id=1, name="Project Delta", path="~/delta", first_seen=now, last_seen=now, session_count=1, total_time=600)
    cmd = Command(timestamp=now, command="git diff", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 600, duration_seconds=600, project_id=1, commands=[cmd], commits=[
        {"hash": "abcdefabcdef", "timestamp": now, "message": "feat: init", "cleaned_message": "Init"}
    ])
    
    output = format_week_output([s], [p], now - 3600, now + 3600)
    assert "This Week" in output
    assert "Project Delta" in output
    assert "Total Time:" in output
    assert "Git" in output

def test_formatter_month_output():
    now = int(time.time())
    p = Project(id=1, name="Project Delta", path="~/delta", first_seen=now, last_seen=now, session_count=1, total_time=600)
    cmd = Command(timestamp=now, command="git diff", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 600, duration_seconds=600, project_id=1, commands=[cmd])
    
    output = format_month_output([s], [p], 2026, 6)
    assert "Project Delta" in output
    assert "Total Work Days:" in output

def test_formatter_project_output():
    now = int(time.time())
    p = Project(id=1, name="Project Delta", path="~/delta", first_seen=now, last_seen=now, session_count=1, total_time=600)
    cmd = Command(timestamp=now, command="git diff", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 600, duration_seconds=600, project_id=1, commands=[cmd], commits=[
        {"hash": "abcdefabcdef", "timestamp": now, "message": "feat: init", "cleaned_message": "Init"}
    ])
    
    output = format_project_output([s], p)
    assert "Project Delta" in output
    assert "Init" in output

def test_formatter_projects_list():
    now = int(time.time())
    p = Project(id=1, name="Project Delta", path="~/delta", first_seen=now, last_seen=now, session_count=1, total_time=600)
    
    output = format_projects_list([p])
    assert "Your Projects" in output
    assert "Project Delta" in output

def test_formatter_detailed_sessions():
    now = int(time.time())
    cmd = Command(timestamp=now, command="git diff", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 600, duration_seconds=600, project_id=1, commands=[cmd])
    
    output = format_detailed_sessions([s])
    assert "SESSION 1:" in output
    assert "git diff" in output

def test_formatter_search_results():
    # Tuesday, June 2nd, 2026
    now = 1772481600 # 2026-06-02 12:00:00 UTC
    results = [{
        "session_id": 1,
        "start_time": now,
        "end_time": now + 600,
        "duration_seconds": 600,
        "project_id": 1,
        "project_name": "Project Delta",
        "project_path": "~/delta",
        "all_commands": ["git diff"],
        "matching_commands": ["git diff"],
        "all_commits": [{"hash": "abcdefabcdef", "timestamp": now, "message": "feat: init", "cleaned_message": "Init"}],
        "matching_commits": [{"hash": "abcdefabcdef", "timestamp": now, "message": "feat: init", "cleaned_message": "Init"}]
    }]
    
    # 1. Test default mode
    output = format_search_results("git", results, detailed=False)
    
    min_dt = datetime.fromtimestamp(now)
    expected_date = min_dt.strftime('%b %d')
    
    assert "git" in output.lower()
    assert "Project Delta" in output
    assert "────────────────────" in output
    # Check alignment and text
    assert f"{expected_date}  Init" in output

    # 2. Test detailed mode
    detailed_output = format_search_results("git", results, detailed=True)
    assert "MATCH 1: Session 1" in detailed_output
    assert "Project: Project Delta" in detailed_output
    assert "Init" in detailed_output
    assert "git diff" in detailed_output

def test_formatter_insights_output(monkeypatch):
    now = int(time.time())
    p = Project(id=1, name="Project Delta", path="~/delta", first_seen=now, last_seen=now, session_count=1, total_time=3600)
    cmd = Command(timestamp=now, command="git diff", session_id=1, project_id=1)
    s = Session(id=1, start_time=now, end_time=now + 3600, duration_seconds=3600, project_id=1, commands=[cmd], commits=[
        {"hash": "abcdefabcdef", "timestamp": now, "message": "feat: init", "cleaned_message": "Init"}
    ])
    
    monkeypatch.setattr("termstory.database.Database.get_range_sessions", lambda self, start, end: [s])
    monkeypatch.setattr("termstory.database.Database.get_projects_by_ids", lambda self, ids: [p])
    
    insights_data = {
        "days": 30,
        "focus_score": 8.5,
        "time_dist": [("Project Delta", 100.0, 3600)],
        "tod_dist": {"morning": 3600, "afternoon": 0, "evening": 0},
        "day_dist": {"Monday": 3600, "Tuesday": 0, "Wednesday": 0, "Thursday": 0, "Friday": 0, "Saturday": 0, "Sunday": 0},
        "patterns": ["Active morning developer"]
    }
    
    output = format_insights_output(insights_data)
    assert "Highlights" in output
    assert "Project Delta" in output
    assert "Init" in output
