import pytest
import asyncio
from termstory.tui import TermStoryWorkspace

from termstory.database import Database
from textual.events import Resize
from textual.geometry import Size

@pytest.mark.asyncio
async def test_resize_race_conditions(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(str(db_file))
    db.init_db()
    app = TermStoryWorkspace(db=db)
    
    async with app.run_test() as pilot:
        for i in range(100):
            # rapid resizing
            app.post_message(Resize(Size(80 + i % 20, 24 + i % 10), Size(0, 0)))
            await asyncio.sleep(0.01)
        
        # Check if app is still responsive
        assert app.is_running
