"""
tests/test_performance.py
=========================
Lightweight performance and N+1 query regression tests for TermStory.

These tests assert that:
  1. Bulk DB operations complete within acceptable time budgets.
  2. The session-loading path does NOT exhibit N+1 query patterns
     (i.e., commit/project lookups are batched, not issued per-session).
"""

import time
import sqlite3
import tempfile
import os
import unittest
from unittest.mock import patch, MagicMock

from termstory.database import Database
from termstory.session import create_sessions
from termstory.models import Command, Session, Project


def _make_commands(n: int, base_ts: int = 1_700_000_000) -> list:
    cmds = []
    for i in range(n):
        cmd = Command(
            command=f"echo task_{i}",
            timestamp=base_ts + i * 10,
            project_id=1,
            session_id=None,
        )
        cmds.append(cmd)
    return cmds


class TestBulkIngestionPerformance(unittest.TestCase):
    """Verify that ingesting 500 commands completes in under 5 seconds."""

    def test_bulk_save_performance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "perf.db")
            db = Database(db_path)
            db.init_db()

            commands = _make_commands(500)
            sessions = create_sessions(commands)
            project = Project(
                id=1, name="PerfProject", path=tmpdir,
                first_seen=commands[0].timestamp,
                last_seen=commands[-1].timestamp,
                session_count=len(sessions),
                total_time=commands[-1].timestamp - commands[0].timestamp,
            )
            for sess in sessions:
                sess.project_id = 1

            start = time.perf_counter()
            db.save_data([project], sessions, commands)
            elapsed = time.perf_counter() - start

            self.assertLess(
                elapsed, 5.0,
                f"Bulk save of 500 commands took {elapsed:.2f}s — exceeds 5s budget"
            )


class TestNoPlusOneQueryPattern(unittest.TestCase):
    """
    Verify that session loading does NOT exhibit N+1 query patterns
    (i.e., commit/project lookups are batched, not issued per-session).
    We ingest enough commands to produce multiple sessions, then count
    sqlite3.connect calls during get_range_sessions. The call count must
    be O(1) (≤ 5), not O(N_sessions).
    """

    def test_range_sessions_is_not_n_plus_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "n1check.db")
            db = Database(db_path)
            db.init_db()

            # Space commands 40 minutes apart to force many distinct sessions
            n_cmds = 30
            base_ts = 1_700_000_000
            commands = []
            for i in range(n_cmds):
                cmd = Command(
                    command=f"echo task_{i}",
                    timestamp=base_ts + i * 40 * 60,  # 40 min gap → new session each time
                    project_id=1,
                    session_id=None,
                )
                commands.append(cmd)

            sessions = create_sessions(commands)
            # 30 commands 40 min apart → each is its own session (gap > 30 min threshold)
            self.assertGreater(len(sessions), 5, "Need multiple sessions for N+1 check")

            project = Project(
                id=1, name="N1Project", path=tmpdir,
                first_seen=commands[0].timestamp,
                last_seen=commands[-1].timestamp,
                session_count=len(sessions),
                total_time=500,
            )
            for sess in sessions:
                sess.project_id = 1
            db.save_data([project], sessions, commands)

            # Count real sqlite3.connect calls during session load
            connect_calls = []
            original_connect = sqlite3.connect

            def tracking_connect(*args, **kwargs):
                connect_calls.append(args)
                return original_connect(*args, **kwargs)

            with patch("termstory.database.sqlite3.connect", side_effect=tracking_connect):
                _ = db.get_range_sessions(0, 2_000_000_000)

            n_sessions = len(sessions)
            n_connects = len(connect_calls)
            # Expect O(1) connections — a generous upper bound of 5 vs. N sessions
            self.assertLessEqual(
                n_connects, 5,
                f"N+1 detected: {n_connects} DB connections for {n_sessions} sessions. "
                "Session loading must use batched queries."
            )


if __name__ == "__main__":
    unittest.main()
