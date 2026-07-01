# AI Medical Coding System (ICD-10-CM + ICD-10-PCS)

A production-grade, local-first AI-assisted medical coding platform. Doctors submit clinical notes, an agentic LangGraph workflow retrieves candidate ICD-10 codes via hybrid vector search in Qdrant, a Groq LLM filters and justifies selections using a step-by-step ReAct pattern, and human coders audit and finalize recommendation states.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Doctor[Doctor / Clinical Note] -->|Submits Dictation| API[FastAPI Backend]
    API -->|Triggers Workflow| Safety[Security: Safety & Redaction Node]
    Safety -->|Redacted Note| RAG[RAG Retrieval Node]
    RAG -->|Queries| Qdrant[(Qdrant Vector DB)]
    RAG -->|Candidate Codes| Agent[LLM Coding Agent Node]
    Agent -->|Groq Llama 3| Filter[Verify & Justify Candidates]
    Filter -->|AI suggested codes| DB[(SQLite DB)]
    DB -->|Awaiting Audit| Coder[Coder Dashboard]
    Coder -->|Audit & Approves/Overrides| DB
    DB -->|Finalized ICD Codes| Final[Saved Records & Traces]
    Final -->|Latency & Prompt Logs| Langfuse[Langfuse Tracing]
```

## 🔄 Execution Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Doctor
    actor Coder
    participant API as FastAPI Backend
    participant Graph as LangGraph Workflow
    participant Qdrant as Qdrant Vector DB
    participant LLM as Groq LLM
    participant DB as SQLite Database
    participant LF as Langfuse Observability
    
    Doctor->>API: POST /api/coding/notes (Dictation)
    API->>DB: Save Note (status: pending)
    API->>Graph: Run Coding Workflow
    rect rgb(30, 41, 59)
        note right of Graph: Safety & PHI Redaction
        Graph->>Qdrant: Hybrid Retrieval (query vector + words)
        Qdrant-->>Graph: Candidate CM & PCS Codes
        Graph->>LLM: Analyze note and extract matches from candidate list
        LLM-->>Graph: Selected Codes + Justifications (ReAct Thought/Action)
        Graph->>Graph: Confidence Check
    end
    Graph->>DB: Save AI Suggestions (CodingResult)
    Graph->>DB: Update Note status to 'reviewed'
    Graph->>LF: Record complete trace (latency, inputs, outputs)
    API-->>Doctor: Note status updated to 'reviewed'
    
    Coder->>API: GET /api/coding/notes (Audit list)
    API->>DB: Fetch reviewed notes
    DB-->>Coder: Notes waiting for approval
    Coder->>API: GET /api/coding/notes/{id}/ai-suggestions
    API-->>Coder: Suggested codes & justifications
    Coder->>Coder: Override, add or delete codes
    Coder->>API: POST /api/coding/approvals (Finalized codes)
    API->>DB: Create Approval & link final_codes_id to Note
    API->>DB: Update Note status to 'approved'
    API->>DB: Write AuditLog entry
    API-->>Coder: Approved codes finalized!
    
    Doctor->>API: GET /api/coding/notes/{id}/final
    API->>DB: Fetch approved codes mapping
    DB-->>Doctor: View Final ICD Codes
```

---

## 🛠️ Setup Instructions

### Prerequisites
*   **Docker & Docker Compose** (minimum v2.0)
*   **Python 3.12+** (managed locally via `uv` or system pip)
*   **Node.js 20+ & npm** (for frontend development)
*   **Groq API Key** (register on [Groq Console](https://console.groq.com/))

### 1. Local Environment Configuration
Create a `.env` file at the project root directory. Here is the template to use:
```env
APP_NAME=AIMedicalCoding
ENV=development
DEBUG=True
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
JWT_SECRET=super-secret-key-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440
GROQ_API_KEY=your_actual_groq_key
GROQ_MODEL=llama-3.1-8b-instant
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_ICD10_CM=icd10_cm
QDRANT_COLLECTION_ICD10_PCS=icd10_pcs
LANGFUSE_PUBLIC_KEY=pk-lf-d50622fa-af43-44ed-8e9d-9dde050b2733
LANGFUSE_SECRET_KEY=sk-lf-a41e935a-3d8a-48c7-9a22-a0d3ef06ec77
LANGFUSE_HOST=http://langfuse:3000
EMBEDDING_MODEL=all-MiniLM-L6-v2
SQLITE_DB_PATH=sqlite:///./medical_coding.db
ICD10_CM_PATH=data/icd10-cm
ICD10_PCS_PATH=data/icd10-pcs
PROCESSED_DATA_PATH=data/processed
```

---

### 2. Running stack via Docker Compose
To boot up the complete pipeline (Postgres, Qdrant Vector database, Langfuse tracing dashboard, FastAPI backend, and Next.js frontend application):
```bash
# Clear any legacy cached volumes and rebuild
docker-compose down
docker-compose up -d --build
```
*   **Frontend Client**: `http://localhost:3001`
*   **Backend OpenAPI Swagger**: `http://localhost:8000/docs`
*   **Langfuse Dashboard**: `http://localhost:3000`
*   **Qdrant Vector Dashboard**: `http://localhost:6333/dashboard`

---

### 3. ICD-10 Vector Ingestion
Vectorize raw ICD-10 order files to the Qdrant DB. Put your descriptors in `data/icd10-cm/` and `data/icd10-pcs/`.

#### Ingest Diagnostic Codes (CM)
```bash
docker exec -it ai-medical-coding-backend-1 uv run icd-ingest --type cm
```

#### Ingest Procedural Codes (PCS)
```bash
docker exec -it ai-medical-coding-backend-1 uv run icd-ingest --type pcs
```

---

## 🔒 Security & Safety Guardrails

The application enforces strict compliance and moderation protocols:

*   **PHI Redaction**: High-precision regex engines intercept medical inputs inside `security.py`, stripping out SSNs, phone numbers, email addresses, and doctor/patient names before conveying text to public LLM APIs.
*   **NVIDIA NeMo Guardrails**: Integrated using `nemoguardrails` with custom Colang definitions:
    *   **Prompt Injections**: Intercepts instructions-override attempts (e.g. *"Ignore all previous instructions"*).
    *   **Off-Topic Filtering**: Blocks non-clinical conversational attempts (e.g. asking for cookie recipes).
*   **Fallback Protections**: If NeMo Guardrails has connection failures or rate limits, the safety node falls back to local regex validation checks.

---

## 📈 System observability (Langfuse)

All workflow invocations are instrumented via **Langfuse** (SDK v2). The system propagates `trace_id` through the LangGraph State, creating observations (spans and generations):
*   Tracks LLM input/output tokens, temperature, and API response latencies.
*   Observes hybrid vector search extraction metrics.
*   Allows developers to grade outputs, inspect security blocks, and monitor prompt latency trends.

---

## 🧠 ReAct reasoning Pattern
The Coding Agent uses the **Reasoning and Action (ReAct)** pattern to improve medical coding accuracy:
*   Before confirming a code, the agent outputs a structured step-by-step reasoning analysis.
*   It justifies the diagnostic criteria and rules out non-applicable alternative codes.
*   **Format**: The output is returned within the `"reason"` field:
    `"THOUGHT: [Analyze symptoms and patient findings against code description, rule out conflicts] ACTION: [Confirm selection of this code]"`
*   This details the AI's logic directly on the coder dashboard.

---

## 🧪 Systematic evaluations (Evals)
We implement offline evaluations using the **`openevals`** library to prevent quality regression:
*   **Evaluations script**: Runs base cases from a clinical note benchmark dataset and aggregates **Precision**, **Recall**, and **F1-scores**.
*   **Exact Match Rate**: Compares lists of suggested codes against reference answers using `openevals.exact.exact_match`.
*   **Full 1,000 scaling runs**: Simulates metric distributions by running core benchmarks alongside 990 variant runs to check scaling reliability.

Run evaluations using:
```bash
docker exec -it ai-medical-coding-backend-1 /app/.venv/bin/python -m backend.tests.run_evals
```

---

## 🖼️ Application Scenario Walkthroughs

Below is a walkthrough of common application scenarios:

### 1. Doctor Dashboard (Clinical Submission)
Doctors submit clinical dictations. High-confidence notes auto-approve and move directly to approved state, while medium-confidence notes enter the human audit queue.

![Doctor Dashboard](docs/images/doctor_dashboard.png)

### 2. Coder Audit Workspace
Human coders open the audit queue to inspect the recommended codes alongside the step-by-step ReAct thought/action justifications. Coders can manually override, append, or delete codes before finalizing the record.

![Coder Audit Panel](docs/images/auditor_panel.png)

### 3. Approved History Log
Once finalized, notes update to **Approved** across both Doctor and Coder interfaces, showing the final audited ICD codes list.

![Approved History](docs/images/doctor_dashboard_after_submit.png)
