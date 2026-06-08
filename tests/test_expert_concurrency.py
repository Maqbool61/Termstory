import sqlite3
import threading
import time
import os
import random
from termstory.database import Database
from termstory.models import Project, Session, Command

DB_PATH = "test_expert_concurrency.db"

def worker(worker_id):
    db = Database(DB_PATH)
    db.init_db()
    for i in range(50):
        try:
            # Create some mock data
            p = Project(name=f"proj_{worker_id}_{i}", path=f"/tmp/proj_{worker_id}_{i}")
            p.id = i
            s = Session(start_time=int(time.time()), end_time=int(time.time())+10, project_id=i)
            s.id = i
            c = Command(timestamp=int(time.time()), command=f"echo {worker_id} {i}", session_id=i, is_legacy=False)
            db.save_data([p], [s], [c])
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print(f"Worker {worker_id} hit database lock: {e}")
            else:
                print(f"Worker {worker_id} sqlite error: {e}")
        except Exception as e:
            print(f"Worker {worker_id} error: {e}")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    threads = []
    start = time.time()
    for i in range(20): # 20 concurrent threads
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    print(f"Finished concurrency test in {time.time() - start:.2f}s")
    
    db = Database(DB_PATH)
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM commands")
    print(f"Commands inserted: {c.fetchone()[0]}")
