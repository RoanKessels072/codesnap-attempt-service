from sqlalchemy import Column, Integer, Text, DateTime, String
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class Attempt(Base):
    __tablename__ = 'user_exercise_attempts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    exercise_id = Column(Integer, nullable=False)
    
    code_submitted = Column(Text, nullable=False)
    score = Column(Integer, nullable=False, default=0)
    stars = Column(Integer, nullable=False, default=0)
    attempted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), nullable=False, default='pending')