---
title: Data Layer
description: ORM, repository pattern, and migrations in LarryBot2
last_updated: 2025-06-28
---

# Data Layer 🗄️

LarryBot2 uses SQLAlchemy ORM and the repository pattern for robust, testable data access.

## 🗃️ ORM Usage
- SQLAlchemy models for tasks, clients, reminders, etc.
- Declarative model definitions
- Relationships for foreign keys and associations

## 🏛️ Repository Pattern
- Abstracts data access from business logic
- Each entity has a repository (e.g., TaskRepository)
- Enables easy mocking and testing

## 🛠️ Example: Repository Usage
```python
from larrybot.storage.task_repository import TaskRepository

task_repo = TaskRepository(session)
tasks = task_repo.get_all_incomplete()
```

## 🔄 Migrations
- Alembic for schema migrations
- Versioned migration scripts in `alembic/versions/`
- Run migrations with:
```bash
alembic upgrade head
```

## 🛡️ Data Integrity
- Use constraints and validation in models
- Handle exceptions in repositories
- Regularly back up the database

## ⚡ Performance Optimizations

### SQLite Configuration
LarryBot2 uses optimized SQLite settings for better concurrency and performance:

```python
# WAL mode for better concurrency (readers don't block writers)
PRAGMA journal_mode=WAL

# 30-second busy timeout (reduced lock contention)
PRAGMA busy_timeout=30000

# Optimized synchronization for better performance
PRAGMA synchronous=NORMAL

# 64MB cache for improved query performance
PRAGMA cache_size=-64000
```

### Connection Pooling
- **Pool pre-ping**: Verify connections before use
- **Pool recycling**: Connections recycled every 5 minutes
- **Timeout handling**: 20-second connection timeout
- **Thread safety**: Connections shared safely between threads

### Bulk Operations
- **Bulk deletes**: Multiple records deleted in single queries
- **Batched commits**: Reduced transaction overhead
- **Efficient queries**: Optimized for large datasets
- **Performance monitoring**: Automatic detection of slow operations

## 📊 Performance Monitoring

### Automatic Detection
```python
execution_time = time.time() - start_time
if execution_time > 1.0:
    logger.warning(f"Operation took {execution_time:.2f}s - potential performance issue")
```

### Key Metrics
- **Database query time**: Should be <100ms for simple queries
- **Bulk operation time**: Should be <1 second
- **Connection acquisition**: Should be <50ms
- **Lock contention**: Minimal with WAL mode

## 🛠️ Best Practices

### Database Operations
- Keep models and repositories in sync
- Use transactions for multi-step operations
- Write tests for all repository methods
- **Use bulk operations for multiple records**
- **Monitor query performance automatically**
- **Implement proper session management**

### Performance Guidelines
- **Session management**: Use short-lived sessions with timeouts
- **Query optimization**: Use efficient queries with proper indexing
- **Bulk operations**: Batch multiple operations together
- **Monitoring**: Implement automatic performance detection

### Database Configuration
- **Enable WAL mode**: For better concurrency
- **Set busy timeouts**: To handle lock contention
- **Configure cache size**: For improved read performance
- **Use connection pooling**: For efficient connection management

---

**Related Guides**: [Architecture Overview](overview.md) | [Testing](../development/testing.md) | [Performance Guide](../performance/README.md) 