from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class PredictRequest(BaseModel):
    input_data: List[float] = Field(..., description="Array of input floats")
    model_version: str = Field(default="v1")
    priority: int = Field(default=0, ge=0, le=10)

class PredictResponse(BaseModel):
    job_id: UUID
    status: str
    queued_at: datetime

class ResultResponse(BaseModel):
    job_id: UUID
    status: str
    result: Optional[List[float]] = None
    latency_ms: Optional[float] = None
