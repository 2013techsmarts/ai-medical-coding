from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class NoteCreate(BaseModel):
    content: str

class NoteResponse(BaseModel):
    id: int
    doctor_id: int
    content: str
    status: str
    created_at: datetime
    final_codes_id: Optional[int] = None

    class Config:
        from_attributes = True

class ICDCodeInfo(BaseModel):
    code: str
    description: str
    type: str # "cm" or "pcs"
    score: Optional[float] = None

class CodingResultResponse(BaseModel):
    id: int
    note_id: int
    ai_suggested_codes: List[ICDCodeInfo]
    confidence_score: str
    created_at: datetime

    class Config:
        from_attributes = True

class ApprovalCreate(BaseModel):
    coding_result_id: int
    final_codes: List[ICDCodeInfo]

class ApprovalResponse(BaseModel):
    id: int
    coding_result_id: int
    coder_id: Optional[int] = None
    final_codes: List[ICDCodeInfo]
    approved_at: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    action: str
    user_id: Optional[int] = None
    entity: str
    entity_id: int
    details: str
    timestamp: datetime

    class Config:
        from_attributes = True
