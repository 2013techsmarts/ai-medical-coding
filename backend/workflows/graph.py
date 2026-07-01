from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from ..config.config import settings
from ..rag.retrieval import icd_retriever
from .security import redact_phi, detect_prompt_injection
from langfuse import Langfuse
import json
import re
import logging
import os
from nemoguardrails import LLMRails, RailsConfig

logger = logging.getLogger(__name__)

# Initialize Langfuse client
langfuse = None
if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
    langfuse = Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST
    )

# Cache NeMo Guardrails client
rails_client = None

def get_rails_client():
    global rails_client
    if rails_client is None:
        try:
            if settings.GROQ_API_KEY:
                os.environ["OPENAI_API_KEY"] = settings.GROQ_API_KEY
                os.environ["OPENAI_API_BASE"] = "https://api.groq.com/openai/v1"
            config_path = os.path.join(os.path.dirname(__file__), "guardrails_config")
            config = RailsConfig.from_path(config_path)
            rails_client = LLMRails(config)
        except Exception as e:
            logger.warning(f"Failed to initialize NeMo Guardrails: {e}")
    return rails_client

class WorkflowState(TypedDict):
    clinical_note: str
    redacted_note: str
    retrieved_codes: List[Dict[str, Any]]
    recommended_codes: List[Dict[str, Any]]
    confidence: str
    error: Optional[str]
    trace_id: Optional[str]

# Node 1: Redaction & Safety Check
def check_safety_and_redact(state: WorkflowState) -> WorkflowState:
    note = state["clinical_note"]
    
    # 1. NeMo Guardrails input checks
    rails = get_rails_client()
    if rails:
        try:
            response = rails.generate(prompt=note)
            if "Potential security validation failure" in response or "blocked by NVIDIA Guardrails" in response:
                return {
                    **state,
                    "redacted_note": "",
                    "error": "Potential security validation failure: blocked by NVIDIA Guardrails",
                    "recommended_codes": []
                }
        except Exception as e:
            logger.warning(f"NeMo Guardrails evaluation failed: {e}")
            
    # 2. Fallback / Additional Prompt Injection Detection
    if detect_prompt_injection(note):
        return {
            **state,
            "redacted_note": "",
            "error": "Potential security validation failure: prompt injection detected",
            "recommended_codes": []
        }
    
    # 3. PHI Redaction
    redacted = redact_phi(note)
    return {
        **state,
        "redacted_note": redacted
    }

# Node 2: RAG Code Retrieval
def retrieve_icd_codes(state: WorkflowState) -> WorkflowState:
    if state.get("error"):
        return state

    note = state["redacted_note"]
    trace_id = state.get("trace_id")
    retrievals = []

    # Use Langfuse Span for retrieval tracing
    if langfuse and trace_id:
        try:
            span = langfuse.span(
                trace_id=trace_id,
                name="retrieve_qdrant",
                input=note
            )
            candidates_dict = icd_retriever.retrieve(note, limit=8)
            retrievals = candidates_dict["cm"] + candidates_dict["pcs"]
            span.end(output=json.dumps(retrievals), metadata={"count": len(retrievals)})
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            retrievals = []
    else:
        try:
            candidates_dict = icd_retriever.retrieve(note, limit=8)
            retrievals = candidates_dict["cm"] + candidates_dict["pcs"]
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            retrievals = []

    return {
        **state,
        "retrieved_codes": retrievals
    }

# Node 3: LLM Coding Agent
def coding_agent(state: WorkflowState) -> WorkflowState:
    if state.get("error"):
        return state

    note = state["redacted_note"]
    retrieved = state["retrieved_codes"]
    
    if not retrieved:
        return {
            **state,
            "recommended_codes": [],
            "confidence": "low"
        }
        
    # If API key is empty, run mock mapping to avoid crashing
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set. Falling back to exact matching.")
        note_lower = note.lower()
        rec_codes = []
        for c in retrieved:
            words = set(c["description"].lower().split())
            if any(w in note_lower for w in words if len(w) > 3):
                rec_codes.append(c)
        if not rec_codes:
            rec_codes = [retrieved[0]]
        return {
            **state,
            "recommended_codes": rec_codes,
            "confidence": "medium"
        }

    # Setup LLM coding prompt
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a highly precise Medical Coding AI. 
Your task is to analyze the redacted clinical note and select the most appropriate ICD-10 codes ONLY from the provided candidate list.
CRITICAL CONSTRAINT: You MUST NOT suggest any code that is NOT in the candidate list. Do not hallucinate or create new codes.

For each candidate code, you must execute a step-by-step reasoning (Thought) and selection decision (Action) loop.
Format your response as a valid JSON array of objects containing the fields:
- "code": the selected code (must match candidate list exactly)
- "reason": your detailed step-by-step justification structured precisely as:
  "THOUGHT: [Analyze symptoms and patient findings against code description, rule out conflicts] ACTION: [Confirm selection of this code]"

Candidates List:
{candidates}
"""),
        ("human", "Clinical Note:\n{note}")
    ])
    
    candidates_str = "\n".join([f"- Code: {c['code']} | Description: {c['description']} | Type: {c['type']}" for c in retrieved])
    
    try:
        llm = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.1
        )
        
        chain = prompt_template | llm
        
        # Invoke LLM with generation trace
        generation = None
        trace_id = state.get("trace_id")
        if langfuse and trace_id:
            try:
                generation = langfuse.generation(
                    trace_id=trace_id,
                    name="coding_agent_llm",
                    model=settings.GROQ_MODEL,
                    input=note
                )
            except Exception as e:
                logger.error(f"Langfuse generation trace start failed: {e}")

        response = chain.invoke({"candidates": candidates_str, "note": note})
        content = response.content.strip()
        
        if generation:
            try:
                generation.end(output=content)
            except Exception as e:
                logger.error(f"Langfuse generation trace end failed: {e}")

        # Parse JSON output
        if "```" in content:
            content = re.sub(r'```(?:json)?\s*(.*?)\s*```', r'\1', content, flags=re.DOTALL)
            
        selections = json.loads(content)
        
        valid_codes = {c["code"]: c for c in retrieved}
        recommended = []
        
        for item in selections:
            code = item.get("code")
            if code in valid_codes:
                recommended.append({
                    "code": code,
                    "description": valid_codes[code]["description"],
                    "type": valid_codes[code]["type"],
                    "score": valid_codes[code].get("score"),
                    "reason": item.get("reason", "")
                })
                
        return {
            **state,
            "recommended_codes": recommended
        }
        
    except Exception as e:
        logger.error(f"LLM Agent workflow error: {e}")
        return {
            **state,
            "recommended_codes": [retrieved[0]] if retrieved else [],
            "confidence": "low",
            "error": f"LLM error: {str(e)}"
        }

# Node 4: Confidence Check
def confidence_check(state: WorkflowState) -> WorkflowState:
    rec = state.get("recommended_codes", [])
    if not rec:
        return {
            **state,
            "confidence": "low"
        }
        
    has_reasons = all("reason" in c and c["reason"] for c in rec)
    
    # Auto-elevate to high confidence (auto-approval) only if there is a strong RAG match (score >= 0.9)
    has_high_score = any(c.get("score") is not None and c.get("score", 0) >= 0.9 for c in rec)
    
    # Needs justifications AND high matching score to auto-approve
    is_high = has_high_score and has_reasons and not state.get("error")
    
    # Fallback to high confidence if LLM failed but we have a strong/exact match
    if state.get("error") and has_high_score:
        is_high = True
    
    return {
        **state,
        "confidence": "high" if is_high else "medium"
    }

# Build Workflow Graph
workflow = StateGraph(WorkflowState)

workflow.add_node("redact_and_safety", check_safety_and_redact)
workflow.add_node("retrieve_candidates", retrieve_icd_codes)
workflow.add_node("llm_coding_agent", coding_agent)
workflow.add_node("confidence_check", confidence_check)

workflow.set_entry_point("redact_and_safety")

workflow.add_edge("redact_and_safety", "retrieve_candidates")
workflow.add_edge("retrieve_candidates", "llm_coding_agent")
workflow.add_edge("llm_coding_agent", "confidence_check")
workflow.add_edge("confidence_check", END)

compiled_graph = workflow.compile()
