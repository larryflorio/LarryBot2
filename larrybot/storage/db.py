from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from larrybot.models import Base  # Unified Base for all models
from typing import Generator, Optional
import logging
import time
import threading
from contextlib import contextmanager
import weakref

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///larrybot.db"

# Enhanced engine with optimized connection pooling
engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    pool_pre_ping=True,        # Verify connections before use
    pool_recycle=300,          # Recycle connections every 5 minutes
    poolclass=QueuePool,       # Use queue pool for better connection management
    pool_size=10,              # Initial connection pool size
    max_overflow=20,           # Allow up to 20 additional connections
    pool_timeout=30,           # 30 second timeout for getting connection
    connect_args={
        "timeout": 20,             # 20 second timeout for connections
        "check_same_thread": False  # Allow connection sharing between threads
    }
)

# Configure SQLite for better concurrency and performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance and concurrency.""" 
    cursor = dbapi_connection.cursor()
    try:
        # Enable WAL mode for better concurrency (allows readers during writes)
        cursor.execute("PRAGMA journal_mode=WAL")
        # Set busy timeout to 20 seconds (optimized for faster operations)
        cursor.execute("PRAGMA busy_timeout=20000")
        # Optimize synchronization for better performance
        cursor.execute("PRAGMA synchronous=NORMAL")
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        # Optimize cache size (use more memory for better performance)
        cursor.execute("PRAGMA cache_size=-32000")  # 32MB cache (reduced from 64MB)
        # Enable memory-mapped I/O for better performance
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        # Optimize temp storage
        cursor.execute("PRAGMA temp_store=MEMORY")
        logger.debug("SQLite PRAGMA settings applied successfully")
    except Exception as e:
        logger.warning(f"Failed to apply SQLite PRAGMA settings: {e}")
    finally:
        cursor.close()

# Optimized session factory with shorter-lived sessions
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False,       # Manual flush control for better performance
    autocommit=False,      # Manual commit control
    future=True,
    expire_on_commit=False  # Keep objects accessible after commit
)

# Session lifecycle tracking for optimization
class SessionTracker:
    """Track session usage for optimization and memory management."""
    
    def __init__(self):
        self._active_sessions = weakref.WeakSet()
        self._stats = {
            'created': 0,
            'closed': 0,
            'max_concurrent': 0,
            'total_duration': 0.0
        }
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
            
            # Log long-running sessions
            if duration > 5.0:
                logger.warning(f"Long-running session detected: {duration:.2f}s")
    
    def get_stats(self) -> dict:
        """Get session statistics."""
        with self._lock:
            avg_duration = (self._stats['total_duration'] / max(1, self._stats['closed']))
            return {
                'active_sessions': len(self._active_sessions),
                'total_created': self._stats['created'],
                'total_closed': self._stats['closed'],
                'max_concurrent': self._stats['max_concurrent'],
                'avg_duration': f"{avg_duration:.3f}s"
            }

# Global session tracker
_session_tracker = SessionTracker()

def init_db() -> None:
    """
    Create all tables in the database.
    """
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")

# Optimized session context manager for shorter-lived sessions
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
        
        # Set session-specific timeouts for faster operations
        session.execute(text("PRAGMA busy_timeout = 15000"))  # 15 seconds for short sessions
        
        yield session
        
        # Explicit commit for completed operations
        session.commit()
        
    except Exception as e:
        logger.error(f"Session error: {e}")
        session.rollback()
        raise
    finally:
        duration = time.time() - start_time
        _session_tracker.untrack_session(session, start_time)
        
        # Close session promptly to free resources
        session.close()
        
        # Log slow sessions for optimization
        if duration > 2.0:
            logger.warning(f"Slow session detected: {duration:.2f}s")

# Legacy dependency for backward compatibility (now optimized)
def get_session() -> Generator[Session, None, None]:
    """
    Yields an optimized SQLAlchemy session with enhanced lifecycle management.
    """
    with get_optimized_session() as session:
        yield session

# Fast session for read-only operations
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
        # Optimize for read-only operations
        session.execute(text("PRAGMA query_only = ON"))
        session.execute(text("PRAGMA busy_timeout = 5000"))  # 5 seconds for reads
        
        yield session
        
    except Exception as e:
        logger.error(f"Read-only session error: {e}")
        raise
    finally:
        duration = time.time() - start_time
        session.close()
        
        # Log unusually slow read operations
        if duration > 1.0:
            logger.debug(f"Slow read operation: {duration:.2f}s")

# Bulk operation session for efficient batch processing
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
        # Optimize for bulk operations
        session.execute(text("PRAGMA synchronous = OFF"))     # Faster writes (less safe)
        session.execute(text("PRAGMA busy_timeout = 30000"))  # Longer timeout for bulk ops
        session.execute(text("PRAGMA cache_size = -64000"))   # More cache for bulk ops
        
        yield session
        
        # Explicit commit for bulk operations
        session.commit()
        
        # Restore normal synchronous mode
        session.execute(text("PRAGMA synchronous = NORMAL"))
        
    except Exception as e:
        logger.error(f"Bulk session error: {e}")
        session.rollback()
        raise
    finally:
        duration = time.time() - start_time
        session.close()
        
        logger.info(f"Bulk operation completed in {duration:.2f}s")

def get_session_stats() -> dict:
    """Get database session statistics for monitoring."""
    stats = _session_tracker.get_stats()
    
    # Add connection pool stats (SQLite pool has limited methods)
    pool = engine.pool
    try:
        stats.update({
            'pool_size': pool.size(),
            'pool_checked_in': pool.checkedin(),
            'pool_checked_out': pool.checkedout(),
            'pool_overflow': pool.overflow()
        })
    except AttributeError as e:
        # Some pool methods may not be available for SQLite
        logger.debug(f"Pool stats not available: {e}")
        stats['pool_info'] = 'Limited pool stats for SQLite'
    
    return stats

def optimize_database():
    """Run database optimization commands."""
    try:
        with get_optimized_session() as session:
            # Analyze tables for query optimization
            session.execute(text("ANALYZE"))
            
            # Vacuum database to reclaim space (if needed)
            # Note: VACUUM requires exclusive access, so use sparingly
            session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            
            logger.info("Database optimization completed")
            
    except Exception as e:
        logger.error(f"Database optimization failed: {e}")

def close_all_sessions():
    """Close all active sessions and connections (for shutdown)."""
    try:
        # Dispose of the engine connection pool
        engine.dispose()
        logger.info("All database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}") 