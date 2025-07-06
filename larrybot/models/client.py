from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from larrybot.models import Base


class Client(Base):
    """
    SQLAlchemy model for a client.
    All datetime fields are stored as UTC and must be timezone-aware in the application layer.
    """
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(),
        nullable=False)
    tasks = relationship('Task', back_populates='client')
