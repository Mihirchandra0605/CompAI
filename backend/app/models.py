from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from .db import Base


class ComplianceRun(Base):
    __tablename__ = "compliance_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, unique=True, index=True, nullable=False)
    regulation_id = Column(String, index=True, nullable=False)
    status = Column(String, default="PENDING")
    
    # Results
    overall_verdict = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    partial_compliance_score = Column(Float, nullable=True)
    
    # Store the final markdown report
    report_markdown = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
