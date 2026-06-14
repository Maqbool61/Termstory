import json
import os
import time
import re
from typing import List, Dict, Optional, Tuple
from termstory.config import get_app_dir

def get_reminders_file_path() -> str:
    """Return path to reminders JSON file"""
    return os.path.join(get_app_dir("data"), "reminders.json")

def load_reminders() -> List[Dict]:
    """Load all reminders from the JSON file"""
    path = get_reminders_file_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_reminders(reminders: List[Dict]) -> None:
    """Save all reminders to the JSON file"""
    path = get_reminders_file_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reminders, f, indent=4)

def parse_reminder_text(text: str) -> Tuple[str, int]:
    """Parse a phrase like 'remind me about X in N days' or 'X in N days'
    to extract description X and days N.
    """
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Pattern 1: (remind me )?(about|to) <X> in <N> day(s)
    pattern1 = re.compile(
        r"^(?:remind\s+me\s+)?(?:about|to)\s+(.+?)\s+in\s+(\d+)\s+days?$",
        re.IGNORECASE
    )
    m1 = pattern1.match(text)
    if m1:
        return m1.group(1).strip(), int(m1.group(2))
        
    # Pattern 2: <X> in <N> day(s)
    pattern2 = re.compile(r"^(.+?)\s+in\s+(\d+)\s+days?$", re.IGNORECASE)
    m2 = pattern2.match(text)
    if m2:
        return m2.group(1).strip(), int(m2.group(2))
        
    raise ValueError(
        "Could not parse reminder phrase. Please use format like "
        "'remind me about X in N days' or 'X in N days'."
    )

def add_reminder(
    text: str,
    days: Optional[int] = None,
    db = None
) -> Dict:
    """Parse, create, and save a new reminder.
    Associates the reminder with the latest session in the database if available.
    """
    if days is not None:
        # Strip trailing 'in N days' if present in the text to avoid redundancy
        m = re.match(r"^(.+?)\s+in\s+(\d+)\s+days?$", text, re.IGNORECASE)
        if m:
            about = m.group(1).strip()
        else:
            about = text
    else:
        about, days = parse_reminder_text(text)
        
    if days < 0:
        raise ValueError("Days must be a non-negative integer.")

    created_at = int(time.time())
    due_at = created_at + (days * 86400)
    
    # Get latest session if database is provided
    session_id = None
    project_name = "Other"
    
    if db is not None:
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, p.name
                FROM sessions s
                LEFT JOIN projects p ON s.project_id = p.id
                ORDER BY s.start_time DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                session_id = row[0]
                project_name = row[1] or "Other"
        except Exception:
            pass
        finally:
            conn.close()

    reminders = load_reminders()
    
    # Generate next ID
    existing_ids = [r.get("id") for r in reminders if isinstance(r.get("id"), int)]
    next_id = max(existing_ids) + 1 if existing_ids else 1
    
    new_reminder = {
        "id": next_id,
        "about": about,
        "days": days,
        "created_at": created_at,
        "due_at": due_at,
        "session_id": session_id,
        "project_name": project_name,
        "status": "pending"
    }
    
    reminders.append(new_reminder)
    save_reminders(reminders)
    return new_reminder

def complete_reminder(reminder_id: int) -> bool:
    """Mark a reminder as completed"""
    reminders = load_reminders()
    updated = False
    for r in reminders:
        if r.get("id") == reminder_id:
            r["status"] = "completed"
            updated = True
            break
            
    if updated:
        save_reminders(reminders)
    return updated
