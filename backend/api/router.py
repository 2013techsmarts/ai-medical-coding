from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from ..db.database import get_db
from ..db import models
from ..auth.security import get_current_user, check_role
from . import schemas
from ..workflows.orchestrator import run_coding_workflow

router = APIRouter(prefix="/coding", tags=["coding"])

@router.post("/notes", response_model=schemas.NoteResponse, status_code=status.HTTP_201_CREATED)
def submit_note(
    note_in: schemas.NoteCreate, 
    current_user: models.User = Depends(check_role("doctor")), 
    db: Session = Depends(get_db)
):
    # Create the note in DB
    note = models.ClinicalNote(
        doctor_id=current_user.id,
        content=note_in.content,
        status="pending"
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    # Log in audit
    audit = models.AuditLog(
        action="submit_note",
        user_id=current_user.id,
        entity="clinical_note",
        entity_id=note.id,
        details=json.dumps({"content_length": len(note_in.content)})
    )
    db.add(audit)
    db.commit()

    # Trigger LangGraph Workflow asynchronously or synchronously (we do sync for simplicity here)
    try:
        run_coding_workflow(note.id, db)
    except Exception as e:
        # Log failure but return the note
        audit_fail = models.AuditLog(
            action="coding_workflow_failed",
            user_id=current_user.id,
            entity="clinical_note",
            entity_id=note.id,
            details=json.dumps({"error": str(e)})
        )
        db.add(audit_fail)
        db.commit()

    db.refresh(note)
    return note

@router.get("/notes", response_model=List[schemas.NoteResponse])
def get_notes(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role == "doctor":
        return db.query(models.ClinicalNote).filter(models.ClinicalNote.doctor_id == current_user.id).all()
    else: # Coder sees all notes
        return db.query(models.ClinicalNote).all()

@router.get("/notes/{note_id}", response_model=schemas.NoteResponse)
def get_note(
    note_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(models.ClinicalNote).filter(models.ClinicalNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if current_user.role == "doctor" and note.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this note")
    
    return note

@router.get("/notes/{note_id}/ai-suggestions", response_model=schemas.CodingResultResponse)
def get_ai_suggestions(
    note_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(models.ClinicalNote).filter(models.ClinicalNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if current_user.role == "doctor" and note.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view suggestions for this note")
    
    result = db.query(models.CodingResult).filter(models.CodingResult.note_id == note_id).order_by(models.CodingResult.created_at.desc()).first()
    if not result:
        raise HTTPException(status_code=404, detail="No AI suggestions found for this note yet")
    
    # Deserialize suggested codes
    codes = json.loads(result.ai_suggested_codes)
    return schemas.CodingResultResponse(
        id=result.id,
        note_id=result.note_id,
        ai_suggested_codes=codes,
        confidence_score=result.confidence_score,
        created_at=result.created_at
    )

@router.post("/approvals", response_model=schemas.ApprovalResponse)
def approve_coding(
    approval_in: schemas.ApprovalCreate,
    current_user: models.User = Depends(check_role("coder")),
    db: Session = Depends(get_db)
):
    coding_res = db.query(models.CodingResult).filter(models.CodingResult.id == approval_in.coding_result_id).first()
    if not coding_res:
        raise HTTPException(status_code=404, detail="Coding result not found")
    
    note = db.query(models.ClinicalNote).filter(models.ClinicalNote.id == coding_res.note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Associated clinical note not found")

    # Save finalized codes in DB
    final_codes_str = json.dumps([c.model_dump() for c in approval_in.final_codes])
    
    approval = models.Approval(
        coding_result_id=coding_res.id,
        coder_id=current_user.id,
        final_codes=final_codes_str
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    # Link Note to this finalized code approval ID
    note.final_codes_id = approval.id
    note.status = "approved"
    db.commit()

    # Log in audit
    audit = models.AuditLog(
        action="approve_coding",
        user_id=current_user.id,
        entity="approval",
        entity_id=approval.id,
        details=json.dumps({
            "note_id": note.id,
            "final_codes": final_codes_str
        })
    )
    db.add(audit)
    db.commit()

    return schemas.ApprovalResponse(
        id=approval.id,
        coding_result_id=approval.coding_result_id,
        coder_id=approval.coder_id,
        final_codes=json.loads(approval.final_codes),
        approved_at=approval.approved_at
    )

@router.get("/notes/{note_id}/final", response_model=schemas.ApprovalResponse)
def get_final_codes(
    note_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    note = db.query(models.ClinicalNote).filter(models.ClinicalNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if current_user.role == "doctor" and note.doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this note")
    
    if not note.final_codes_id:
        raise HTTPException(status_code=404, detail="Final codes not yet approved for this note")
    
    approval = db.query(models.Approval).filter(models.Approval.id == note.final_codes_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approved coding records not found")

    return schemas.ApprovalResponse(
        id=approval.id,
        coding_result_id=approval.coding_result_id,
        coder_id=approval.coder_id,
        final_codes=json.loads(approval.final_codes),
        approved_at=approval.approved_at
    )

@router.get("/audit-logs", response_model=List[schemas.AuditLogResponse])
def get_audit_logs(
    current_user: models.User = Depends(check_role("coder")), # Coders/Admins can see audit logs
    db: Session = Depends(get_db)
):
    return db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).all()
