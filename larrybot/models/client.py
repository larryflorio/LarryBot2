from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from larrybot.models import Base

class Client(Base):
    """
    SQLAlchemy model for a client.
    """
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationship
    tasks = relationship("Task", back_populates="client") 