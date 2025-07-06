"""
Database models for metrics storage.

This module defines SQLAlchemy models for storing command and system metrics
in the database for persistent analysis and reporting.
Single-user system: all metrics belong to the authorized user.

All datetime fields are stored as UTC and must be timezone-aware in the application layer.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime
Base = declarative_base()


class CommandMetric(Base):
    """Database model for storing command execution metrics."""
    __tablename__ = 'command_metrics'
    id = Column(Integer, primary_key=True)
    command = Column(String(255), nullable=False, index=True)
    execution_time = Column(Float, nullable=False)
    success = Column(Boolean, nullable=False, default=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=
        datetime.now, index=True)
    error_message = Column(Text, nullable=True)
    __table_args__ = Index('idx_command_timestamp', 'command', 'timestamp'
        ), Index('idx_success_timestamp', 'success', 'timestamp')


class SystemMetric(Base):
    """Database model for storing system performance metrics."""
    __tablename__ = 'system_metrics'
    id = Column(Integer, primary_key=True)
    memory_usage = Column(Float, nullable=False)
    cpu_usage = Column(Float, nullable=False)
    active_connections = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=
        datetime.now, index=True)
    __table_args__ = Index('idx_system_timestamp', 'timestamp'),


class UserActivityMetric(Base):
    """Database model for storing user activity metrics."""
    __tablename__ = 'user_activity_metrics'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    command_count = Column(Integer, nullable=False, default=0)
    total_execution_time = Column(Float, nullable=False, default=0.0)
    success_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    __table_args__ = Index('idx_activity_date', 'date'),
