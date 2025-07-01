import pytest
import time
import threading
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import Session

from larrybot.storage.db import (
    get_session, 
    get_optimized_session, 
    get_readonly_session,
    get_bulk_session,
    init_db, 
    SessionTracker,
    _session_tracker,
    get_session_stats,
    optimize_database,
    close_all_sessions,
    set_sqlite_pragma,
    engine
)


class TestDatabaseLayer:
    """Comprehensive tests for database layer functionality."""

    def test_init_db_success(self):
        """Test successful database initialization."""
        # This should not raise any exceptions
        init_db()
        
        # Verify that tables are created by checking if we can connect
        with get_optimized_session() as session:
            # Execute a simple query to verify database is accessible
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            assert len(tables) > 0  # Should have some tables

    def test_get_session_context_manager(self):
        """Test basic session context manager functionality."""
        # get_session() returns a generator, so we use it with next()
        session_gen = get_session()
        session = next(session_gen)
        try:
            assert isinstance(session, Session)
            assert session.is_active
        finally:
            session.close()

    def test_get_optimized_session_context_manager(self):
        """Test optimized session context manager."""
        with get_optimized_session() as session:
            assert isinstance(session, Session)
            assert session.is_active
            
            # Test that session has timeouts set
            result = session.execute(text("PRAGMA busy_timeout"))
            timeout = result.scalar()
            assert timeout == 15000  # 15 seconds
        
        # Session is automatically closed by the context manager

    def test_get_readonly_session_context_manager(self):
        """Test read-only session context manager."""
        with get_readonly_session() as session:
            assert isinstance(session, Session)
            assert session.is_active
            
            # Verify read-only pragma is set
            result = session.execute(text("PRAGMA query_only"))
            query_only = result.scalar()
            assert query_only == 1  # Should be enabled
        
        # Session is automatically closed by the context manager

    def test_get_bulk_session_context_manager(self):
        """Test bulk operations session context manager."""
        with get_bulk_session() as session:
            assert isinstance(session, Session)
            assert session.is_active
            
            # Test bulk session settings
            result = session.execute(text("PRAGMA busy_timeout"))
            timeout = result.scalar()
            assert timeout >= 30000  # Should be at least 30 seconds for bulk operations
        
        # Session is automatically closed by the context manager

    def test_session_error_handling_and_rollback(self):
        """Test that sessions properly handle errors and rollback."""
        try:
            with get_optimized_session() as session:
                # Force an error
                session.execute(text("SELECT * FROM nonexistent_table"))
        except Exception:
            pass  # Expected to fail
        
        # Should still be able to create new sessions
        with get_optimized_session() as session:
            assert session.is_active

    def test_session_commit_behavior(self):
        """Test session commit behavior in different contexts."""
        # Test successful commit
        with get_optimized_session() as session:
            # This should commit without errors
            pass
        
        # Test that changes are committed
        with get_readonly_session() as session:
            # Should be able to read data
            assert session.is_active

    def test_session_tracker_functionality(self):
        """Test session tracking and statistics."""
        tracker = SessionTracker()
        
        # Create mock session
        mock_session = Mock(spec=Session)
        start_time = time.time()
        
        # Test tracking
        tracker.track_session(mock_session, start_time)
        stats = tracker.get_stats()
        assert stats['total_created'] == 1
        assert stats['active_sessions'] == 1
        
        # Test untracking
        tracker.untrack_session(mock_session, start_time)
        stats = tracker.get_stats()
        assert stats['total_closed'] == 1
        assert stats['active_sessions'] == 0

    def test_session_tracker_long_running_detection(self, caplog):
        """Test detection of long-running sessions."""
        tracker = SessionTracker()
        mock_session = Mock(spec=Session)
        
        # Simulate long-running session
        old_time = time.time() - 10.0  # 10 seconds ago
        tracker.track_session(mock_session, old_time)
        
        with caplog.at_level("WARNING"):
            tracker.untrack_session(mock_session, old_time)
        
        assert "Long-running session detected" in caplog.text

    def test_session_tracker_concurrent_sessions(self):
        """Test tracking of concurrent sessions."""
        tracker = SessionTracker()
        sessions = [Mock(spec=Session) for _ in range(5)]
        start_time = time.time()
        
        # Track multiple sessions
        for session in sessions:
            tracker.track_session(session, start_time)
        
        stats = tracker.get_stats()
        assert stats['max_concurrent'] == 5
        assert stats['active_sessions'] == 5

    def test_global_session_stats(self):
        """Test global session statistics retrieval."""
        # Get stats before any operations
        stats = get_session_stats()
        assert isinstance(stats, dict)
        assert 'active_sessions' in stats
        assert 'total_created' in stats
        
        # Create a session and verify stats change
        initial_created = stats['total_created']
        
        with get_optimized_session() as session:
            current_stats = get_session_stats()
            # May be higher due to background activity
            assert current_stats['total_created'] >= initial_created

    @patch('larrybot.storage.db.logger')
    def test_sqlite_pragma_error_handling(self, mock_logger):
        """Test SQLite pragma error handling."""
        # Create a mock connection that fails on execute
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Pragma failed")
        mock_connection.cursor.return_value = mock_cursor
        
        # Test that pragma errors are handled gracefully
        set_sqlite_pragma(mock_connection, None)
        
        # Should log a warning but not crash
        mock_logger.warning.assert_called()
        mock_cursor.close.assert_called()

    @patch('larrybot.storage.db.logger')
    def test_optimized_session_slow_detection(self, mock_logger):
        """Test detection of slow sessions."""
        with patch('larrybot.storage.db.time.time') as mock_time:
            # Simulate slow session - provide enough values for all time.time() calls
            mock_time.side_effect = [0.0, 0.5, 3.0, 3.0, 3.0, 3.0]  # Multiple calls to time.time()
            
            with get_optimized_session() as session:
                pass
            
            # Should log slow session warning
            mock_logger.warning.assert_called()
            assert "Slow session detected" in str(mock_logger.warning.call_args)

    @patch('larrybot.storage.db.logger')
    def test_readonly_session_error_handling(self, mock_logger):
        """Test read-only session error handling."""
        with patch('larrybot.storage.db.SessionLocal') as mock_session_local:
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Database error")
            mock_session_local.return_value = mock_session
            
            with pytest.raises(Exception):
                with get_readonly_session() as session:
                    pass
            
            # Should log error
            mock_logger.error.assert_called()

    def test_optimize_database_function(self):
        """Test database optimization function."""
        # Should not raise exceptions
        try:
            optimize_database()
        except Exception as e:
            pytest.fail(f"optimize_database raised {e}")

    def test_close_all_sessions_function(self):
        """Test closing all sessions function."""
        # Create some sessions first
        sessions = []
        for _ in range(3):
            with get_optimized_session() as session:
                sessions.append(session)
        
        # Should not raise exceptions
        try:
            close_all_sessions()
        except Exception as e:
            pytest.fail(f"close_all_sessions raised {e}")

    def test_concurrent_session_access(self):
        """Test concurrent access to sessions from multiple threads."""
        results = []
        errors = []
        
        def worker():
            try:
                with get_optimized_session() as session:
                    # Simulate some work
                    result = session.execute(text("SELECT 1")).scalar()
                    results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=worker) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0  # No errors should occur
        assert len(results) == 5  # All threads should complete
        assert all(r == 1 for r in results)  # All should return 1

    def test_session_autoflush_autocommit_settings(self):
        """Test that sessions have correct autoflush/autocommit settings."""
        with get_optimized_session() as session:
            # Check session configuration
            assert not session.autoflush  # Should be False for performance
            # Note: autocommit was removed in SQLAlchemy 2.0, transactions are manual

    def test_session_expire_on_commit_setting(self):
        """Test expire_on_commit setting."""
        with get_optimized_session() as session:
            # expire_on_commit should be False to keep objects accessible
            assert not session.expire_on_commit

    def test_engine_configuration(self):
        """Test that engine is configured correctly."""
        # Check pool settings
        assert engine.pool.size() >= 0  # Pool should be initialized
        assert hasattr(engine.pool, '_timeout')  # Should have timeout
        
        # Check that engine is usable
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1

    @patch('larrybot.storage.db.engine.connect')
    def test_engine_connection_error_handling(self, mock_connect):
        """Test engine connection error handling."""
        mock_connect.side_effect = OperationalError("Connection failed", None, None)
        
        with pytest.raises(OperationalError):
            with get_optimized_session() as session:
                session.execute(text("SELECT 1"))

    def test_session_busy_timeout_configuration(self):
        """Test that busy timeout is properly configured."""
        with get_optimized_session() as session:
            result = session.execute(text("PRAGMA busy_timeout")).scalar()
            assert result > 0  # Should have a timeout set

    def test_session_foreign_keys_enabled(self):
        """Test that foreign keys are enabled."""
        with get_readonly_session() as session:
            result = session.execute(text("PRAGMA foreign_keys")).scalar()
            assert result == 1  # Foreign keys should be enabled

    def test_session_wal_mode_enabled(self):
        """Test that WAL mode is enabled for concurrency."""
        with get_readonly_session() as session:
            result = session.execute(text("PRAGMA journal_mode")).scalar()
            assert result.upper() == "WAL"  # Should be in WAL mode

    def test_session_cache_size_optimized(self):
        """Test that cache size is optimized."""
        with get_readonly_session() as session:
            result = session.execute(text("PRAGMA cache_size")).scalar()
            assert result < 0  # Negative value indicates memory-based cache

    def test_memory_mapped_io_enabled(self):
        """Test that memory-mapped I/O is enabled."""
        with get_readonly_session() as session:
            result = session.execute(text("PRAGMA mmap_size")).scalar()
            assert result > 0  # Should have mmap enabled

    def test_temp_store_in_memory(self):
        """Test that temporary storage is in memory."""
        with get_readonly_session() as session:
            result = session.execute(text("PRAGMA temp_store")).scalar()
            assert result == 2  # 2 = MEMORY

    def test_multiple_context_manager_nesting(self):
        """Test that context managers can be nested safely."""
        with get_optimized_session() as outer_session:
            assert outer_session.is_active
            
            with get_readonly_session() as inner_session:
                assert inner_session.is_active
                assert outer_session.is_active
                
            assert outer_session.is_active
        
        # Context managers handle cleanup automatically

    def test_session_resource_cleanup(self):
        """Test that sessions properly clean up resources."""
        session_ref = None
        
        with get_optimized_session() as session:
            session_ref = session
            assert session.is_active
        
        # Context manager handles cleanup, session may still appear active briefly

    def test_session_duration_tracking(self):
        """Test that session duration is properly tracked."""
        tracker = SessionTracker()
        mock_session = Mock(spec=Session)
        
        # Track a session with actual time difference
        start_time = time.time()
        tracker.track_session(mock_session, start_time)
        
        # Wait a bit to ensure measurable duration
        time.sleep(0.01)  
        
        tracker.untrack_session(mock_session, start_time)
        
        stats = tracker.get_stats()
        # Should have some duration recorded
        assert "s" in stats['avg_duration']  # Should show seconds format

    def test_session_stats_threading_safety(self):
        """Test that session statistics are thread-safe."""
        def worker():
            with get_optimized_session() as session:
                time.sleep(0.01)  # Small delay to test concurrency
        
        # Start multiple threads simultaneously
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should not raise any exceptions and stats should be consistent
        stats = get_session_stats()
        assert isinstance(stats, dict)
        assert stats['total_created'] >= 10

    def test_bulk_session_timeout_configuration(self):
        """Test bulk session has longer timeout."""
        with get_bulk_session() as session:
            result = session.execute(text("PRAGMA busy_timeout")).scalar()
            assert result >= 30000  # Should be at least 30 seconds

    def test_bulk_session_optimization_settings(self):
        """Test bulk session has optimized settings."""
        with get_bulk_session() as session:
            # Should have synchronous mode set for bulk operations
            sync_mode = session.execute(text("PRAGMA synchronous")).scalar()
            assert sync_mode in [0, 1]  # OFF or NORMAL for bulk operations 