from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from larrybot.models import Base
from typing import Generator, Optional
import logging
import time
import threading
from contextlib import contextmanager
import weakref
logger = logging.getLogger(__name__)
DATABASE_URL = 'sqlite:///larrybot.db'
engine = create_engine(DATABASE_URL, echo=False, future=True, pool_pre_ping
    =True, pool_recycle=300, poolclass=QueuePool, pool_size=10,
    max_overflow=20, pool_timeout=30, connect_args={'timeout': 20,
    'check_same_thread': False})


@event.listens_for(engine, 'connect')
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance and concurrency."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.execute('PRAGMA busy_timeout=20000')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA cache_size=-32000')
        cursor.execute('PRAGMA mmap_size=268435456')
        cursor.execute('PRAGMA temp_store=MEMORY')
        logger.debug('SQLite PRAGMA settings applied successfully')
    except Exception as e:
        logger.warning(f'Failed to apply SQLite PRAGMA settings: {e}')
    finally:
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False,
    future=True, expire_on_commit=False)


class SessionTracker:
    """Track session usage for optimization and memory management."""

    def __init__(self):
        self._active_sessions = weakref.WeakSet()
        self._stats = {'created': 0, 'closed': 0, 'max_concurrent': 0,
            'total_duration': 0.0}
        self._lock = threading.Lock()

    def track_session(self, session: Session, start_time: float):
        """Track a new session."""
        with self._lock:
            self._active_sessions.add(session)
            self._stats['created'] += 1
            current_count = len(self._active_sessions)
            if current_count > self._stats['max_concurrent']:
                self._stats['max_concurrent'] = current_count

    def untrack_session(self, session: Session, start_time: float):
        """Untrack a closed session."""
        with self._lock:
            if session in self._active_sessions:
                self._active_sessions.discard(session)
            self._stats['closed'] += 1
            duration = time.time() - start_time
            self._stats['total_duration'] += duration
            if duration > 5.0:
                logger.warning(
                    f'Long-running session detected: {duration:.2f}s')

    def get_stats(self) ->dict:
        """Get session statistics."""
        with self._lock:
            avg_duration = self._stats['total_duration'] / max(1, self.
                _stats['closed'])
            return {'active_sessions': len(self._active_sessions),
                'total_created': self._stats['created'], 'total_closed':
                self._stats['closed'], 'max_concurrent': self._stats[
                'max_concurrent'], 'avg_duration': f'{avg_duration:.3f}s'}


_session_tracker = SessionTracker()


def init_db() ->None:
    """
    Create all tables in the database.
    """
    Base.metadata.create_all(bind=engine)
    logger.info('Database initialized successfully')


@contextmanager
def get_optimized_session():
    """
    Context manager for optimized, shorter-lived database sessions.
    
    Features:
    - Automatic session tracking
    - Performance monitoring
    - Automatic cleanup
    - Connection health checks
    """
    start_time = time.time()
    session = SessionLocal()
    try:
        _session_tracker.track_session(session, start_time)
        session.execute(text('PRAGMA busy_timeout = 15000'))
        yield session
        session.commit()
    except Exception as e:
        logger.error(f'Session error: {e}')
        session.rollback()
        raise
    finally:
        duration = time.time() - start_time
        _session_tracker.untrack_session(session, start_time)
        session.close()
        if duration > 2.0:
            logger.warning(f'Slow session detected: {duration:.2f}s')


def get_session() ->Generator[Session, None, None]:
    """
    Yields an optimized SQLAlchemy session with enhanced lifecycle management.
    """
    with get_optimized_session() as session:
        yield session


@contextmanager
def get_readonly_session():
    """
    Context manager for read-only operations with minimal overhead.
    
    Optimized for:
    - Quick data retrieval
    - Minimal locking
    - Faster connection setup
    """
    start_time = time.time()
    session = SessionLocal()
    try:
        session.execute(text('PRAGMA query_only = ON'))
        session.execute(text('PRAGMA busy_timeout = 5000'))
        yield session
    except Exception as e:
        logger.error(f'Read-only session error: {e}')
        raise
    finally:
        duration = time.time() - start_time
        session.close()
        if duration > 1.0:
            logger.debug(f'Slow read operation: {duration:.2f}s')


@contextmanager
def get_bulk_session():
    """
    Context manager for bulk operations with optimized settings.
    
    Optimized for:
    - Batch inserts/updates
    - Reduced transaction overhead
    - Memory efficiency
    """
    start_time = time.time()
    session = SessionLocal()
    try:
        session.execute(text('PRAGMA synchronous = OFF'))
        session.execute(text('PRAGMA busy_timeout = 30000'))
        session.execute(text('PRAGMA cache_size = -64000'))
        yield session
        session.commit()
        session.execute(text('PRAGMA synchronous = NORMAL'))
    except Exception as e:
        logger.error(f'Bulk session error: {e}')
        session.rollback()
        raise
    finally:
        duration = time.time() - start_time
        session.close()
        logger.info(f'Bulk operation completed in {duration:.2f}s')


def get_session_stats() ->dict:
    """Get database session statistics for monitoring."""
    stats = _session_tracker.get_stats()
    pool = engine.pool
    try:
        stats.update({'pool_size': pool.size(), 'pool_checked_in': pool.
            checkedin(), 'pool_checked_out': pool.checkedout(),
            'pool_overflow': pool.overflow()})
    except AttributeError as e:
        logger.debug(f'Pool stats not available: {e}')
        stats['pool_info'] = 'Limited pool stats for SQLite'
    return stats


def optimize_database():
    """Run database optimization commands."""
    try:
        with get_optimized_session() as session:
            session.execute(text('ANALYZE'))
            session.execute(text('PRAGMA wal_checkpoint(TRUNCATE)'))
            logger.info('Database optimization completed')
    except Exception as e:
        logger.error(f'Database optimization failed: {e}')


def close_all_sessions():
    """Close all active sessions and connections (for shutdown)."""
    try:
        engine.dispose()
        logger.info('All database connections closed')
    except Exception as e:
        logger.error(f'Error closing database connections: {e}')
