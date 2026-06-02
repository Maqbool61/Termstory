import time
from termstory.database import Database
from termstory.models import Command, Session, Project

def test_range_queries_and_stats(tmp_path):
    db_file = tmp_path / "test_queries.db"
    db = Database(str(db_file))
    db.init_db()
    
    now = int(time.time())
    
    # Create two projects
    p1 = Project(id=1, name="Apache HugeGraph", path="~/projects/incubator-hugegraph", first_seen=now, last_seen=now, session_count=1, total_time=100)
    p2 = Project(id=2, name="Personal Website", path="~/projects/my-personal-web", first_seen=now + 5000, last_seen=now + 5000, session_count=1, total_time=200)
    
    # Create commands and sessions
    cmd1 = Command(timestamp=now, command="git status", session_id=1, project_id=1)
    s1 = Session(id=1, start_time=now, end_time=now + 100, duration_seconds=100, project_id=1, commands=[cmd1])
    
    cmd2 = Command(timestamp=now + 5000, command="npm install", session_id=2, project_id=2)
    s2 = Session(id=2, start_time=now + 5000, end_time=now + 5200, duration_seconds=200, project_id=2, commands=[cmd2])
    
    db.save_data([p1, p2], [s1, s2], [cmd1, cmd2])
    
    # Test range lookup: start to now + 200 (should only cover first session)
    sessions = db.get_range_sessions(now - 10, now + 300)
    assert len(sessions) == 1
    assert sessions[0].id == s1.id
    
    # Test project sessions lookup
    proj_sessions = db.get_project_sessions(p2.id, now)
    assert len(proj_sessions) == 1
    assert proj_sessions[0].id == s2.id
    
    # Test get all projects with stats
    all_projects = db.get_all_projects_with_stats()
    assert len(all_projects) == 2
    
    hugegraph_proj = next(p for p in all_projects if p.id == p1.id)
    assert hugegraph_proj.session_count == 1
    assert hugegraph_proj.total_time == 100
    
    # Test fuzzy project search
    results = db.search_projects("huge")
    assert len(results) == 1
    assert results[0].name == "Apache HugeGraph"
    
    results = db.search_projects("personal")
    assert len(results) == 1
    assert results[0].name == "Personal Website"
