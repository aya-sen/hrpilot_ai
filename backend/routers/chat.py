from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import ChatMessageCreate, ChatMessageResponse
import backend.models as models
from typing import List
from datetime import datetime

router = APIRouter(
    prefix="/chat",
    tags=["Chat History"]
)

# ── Save a chat message ───────────────────────────────────────────────────────
@router.post("/save", response_model=ChatMessageResponse)
def save_message(employee_id: int, message: str, response: str, db: Session = Depends(get_db)):
    
    employee = db.query(models.Employee).filter(
        models.Employee.employee_id == employee_id
    ).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    new_message = models.ChatHistory(
        employee_id = employee_id,
        message     = message,
        response    = response,
        timestamp   = datetime.now()
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message

# ── Get chat history for an employee ─────────────────────────────────────────
@router.get("/history/{employee_id}", response_model=List[ChatMessageResponse])
def get_history(employee_id: int, limit: int = 20, db: Session = Depends(get_db)):
    
    messages = db.query(models.ChatHistory).filter(
        models.ChatHistory.employee_id == employee_id
    ).order_by(
        models.ChatHistory.timestamp.desc()
    ).limit(limit).all()
    
    # Return in chronological order
    return list(reversed(messages))

# ── Clear chat history for an employee ───────────────────────────────────────
@router.delete("/history/{employee_id}/clear")
def clear_history(employee_id: int, db: Session = Depends(get_db)):
    
    deleted = db.query(models.ChatHistory).filter(
        models.ChatHistory.employee_id == employee_id
    ).delete()
    
    db.commit()
    return {"message": f"Cleared {deleted} messages for employee {employee_id}"}