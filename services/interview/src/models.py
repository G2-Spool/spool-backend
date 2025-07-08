from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, Dict


class InterestData(BaseModel):
    """Model for a single interest"""
    name: str
    details: Optional[str] = None
    detected_at: datetime
    confidence: float = 1.0


class InterviewSession(BaseModel):
    """Model for an interview session"""
    session_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    interests: List[InterestData] = []
    transcript: List[Dict] = []
    metadata: Dict = {}


class InterviewResult(BaseModel):
    """Model for interview results"""
    session_id: str
    user_id: str
    interests: List[InterestData]
    duration: float
    transcript_summary: Optional[str] = None
    langflow_processed: bool = False 