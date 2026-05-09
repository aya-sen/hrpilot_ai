from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

# ── Employee schemas ──────────────────────────────────────────────────────────
class EmployeeResponse(BaseModel):
    employee_id: int
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    gender: str
    birth_date: Optional[date] = None
    city: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    manager_id: Optional[int] = None
    contract_type: str
    hire_date: Optional[date] = None
    salary: Optional[float] = None
    leave_balance_days: int
    status: str
    role: str

    class Config:
        from_attributes = True

# ── Leave Request schemas ─────────────────────────────────────────────────────
class LeaveRequestResponse(BaseModel):
    request_id: int
    employee_id: int
    manager_id: Optional[int] = None
    leave_type: str
    start_date: date
    end_date: date
    duration_days: Optional[int] = None
    status: str
    submission_date: date
    employee_comment:     Optional[str] = None     
    certificate_file_path: Optional[str] = None
    manager_comment: Optional[str] = None

    class Config:
        from_attributes = True

class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    duration_days: int
    employee_comment: Optional[str] = None

# ── Document Request schemas ──────────────────────────────────────────────────
class DocumentRequestResponse(BaseModel):
    doc_request_id: int
    employee_id: int
    document_type: str
    purpose: Optional[str] = None
    status: str
    request_date: date
    generated_file_path: Optional[str] = None
    delivery_date: Optional[date] = None

    class Config:
        from_attributes = True

class DocumentRequestCreate(BaseModel):
    document_type: str
    purpose: Optional[str] = None

# ── Chat schemas ──────────────────────────────────────────────────────────────
class ChatMessageCreate(BaseModel):
    message: str

class ChatMessageResponse(BaseModel):
    chat_id: int
    employee_id: int
    message: str
    response: str
    timestamp: datetime

    class Config:
        from_attributes = True


# ── Internal Rules schemas ────────────────────────────────────────────────────
class InternalRuleResponse(BaseModel):
    rule_id:    int
    category:   str
    title:      str
    content:    str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InternalRuleCreate(BaseModel):
    category: str
    title:    str
    content:  str