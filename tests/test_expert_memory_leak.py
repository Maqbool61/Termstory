import tracemalloc
import time
from termstory.database import Database
from termstory.models import Project, Session, Command

DB_PATH = "test_expert_memory.db"

def run_memory_leak_test():
    db = Database(DB_PATH)
    db.init_db()
    
    # insert dummy data
    for i in range(100):
        p = Project(name=f"proj_{i}", path=f"/tmp/proj_{i}")
        p.id = i
        s = Session(start_time=int(time.time()), end_time=int(time.time())+10, project_id=i)
        s.id = i
        c = Command(timestamp=int(time.time()), command=f"echo {i}", session_id=i, is_legacy=False)
        db.save_data([p], [s], [c])
        
    tracemalloc.start()
    
    # get telemetry multiple times
    from termstory.tui import get_month_wrapped_telemetry
    
    snapshot1 = tracemalloc.take_snapshot()
    
    for i in range(200):
        _ = get_month_wrapped_telemetry(db, "overall")
        
    snapshot2 = tracemalloc.take_snapshot()
    
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print("[ Top 10 memory differences ]")
    for stat in top_stats[:10]:
        print(stat)

if __name__ == "__main__":
    run_memory_leak_test()
