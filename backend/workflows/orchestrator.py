from sqlalchemy.orm import Session
from ..db import models
from .graph import compiled_graph
from langfuse import Langfuse
from ..config.config import settings
import json
import logging

logger = logging.getLogger(__name__)

# Initialize Langfuse client
langfuse = None
if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
    langfuse = Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST
    )

def run_coding_workflow(note_id: int, db: Session):
    """
    Executes the LangGraph agentic medical coding workflow.
    Retrieves the clinical note, processes it through safety checks,
    Qdrant search (RAG), and LLM classification, and saves the output.
    """
    note = db.query(models.ClinicalNote).filter(models.ClinicalNote.id == note_id).first()
    if not note:
        logger.error(f"ClinicalNote with ID {note_id} not found.")
        return

    # Setup tracing in Langfuse
    trace = None
    trace_id = None
    if langfuse:
        try:
            trace = langfuse.trace(
                name="medical_coding_workflow",
                user_id=str(note.doctor_id),
                metadata={"note_id": note_id}
            )
            trace_id = trace.id
        except Exception as e:
            logger.warning(f"Failed to start Langfuse trace: {e}")

    try:
        # Run LangGraph StateGraph
        inputs = {
            "clinical_note": note.content,
            "redacted_note": "",
            "retrieved_codes": [],
            "recommended_codes": [],
            "confidence": "low",
            "error": None,
            "trace_id": trace_id
        }
        
        # Execute workflow
        result_state = compiled_graph.invoke(inputs)
        
        # Extract recommended codes
        recommended = result_state.get("recommended_codes", [])
        confidence = result_state.get("confidence", "low")
        error_msg = result_state.get("error")
        
        if error_msg:
            logger.error(f"Workflow encountered error: {error_msg}")
            
        # Format the recommended codes for database persistence
        formatted_codes = []
        for item in recommended:
            formatted_codes.append({
                "code": item["code"],
                "description": item["description"],
                "type": item["type"],
                "score": item.get("score"),
                "reason": item.get("reason", "Suggested by AI")
            })

        # Save AI Coding Results
        coding_res = models.CodingResult(
            note_id=note_id,
            ai_suggested_codes=json.dumps(formatted_codes),
            confidence_score=confidence
        )
        db.add(coding_res)
        db.flush() # Flush to get coding_res.id for linking
        
        # Auto-Approve if confidence is high, reject if safety validation failed, else mark reviewed
        if error_msg and "security validation failure" in error_msg.lower():
            note.status = "rejected"
        elif confidence == "high":
            approval = models.Approval(
                coding_result_id=coding_res.id,
                coder_id=None, # System Auto-Approved
                final_codes=json.dumps(formatted_codes)
            )
            db.add(approval)
            db.flush() # Flush to get approval.id
            
            note.final_codes_id = approval.id
            note.status = "approved"
            
            # Log in audit
            audit = models.AuditLog(
                action="auto_approve_coding",
                user_id=None, # System action
                entity="approval",
                entity_id=approval.id,
                details=json.dumps({
                    "note_id": note_id,
                    "final_codes": formatted_codes,
                    "reason": "Auto-approved due to high AI confidence score"
                })
            )
            db.add(audit)
        else:
            # Update note status to reviewed, awaiting manual coder audit
            note.status = "reviewed"
            
        db.commit()
        
        # Record trace outcomes
        if trace:
            try:
                trace.update(
                    output=json.dumps(formatted_codes),
                    metadata={
                        "confidence": confidence,
                        "code_count": len(formatted_codes),
                        "status": "success"
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to end Langfuse trace: {e}")

    except Exception as e:
        logger.error(f"Failed to execute coding workflow: {e}")
        db.rollback()
        
        # Mark trace as failed
        if trace:
            try:
                trace.update(
                    metadata={"status": "failed", "error": str(e)}
                )
            except Exception as e_end:
                logger.warning(f"Failed to end Langfuse trace during error handling: {e_end}")
        raise e
    finally:
        if langfuse:
            try:
                langfuse.flush()
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse: {e}")
