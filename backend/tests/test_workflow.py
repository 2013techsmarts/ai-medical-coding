import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.db.database import Base, get_db
import os

# Setup temporary sqlite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_medical_workflow.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Prepopulate users
        from backend.auth.security import get_password_hash
        from backend.db.models import User
        
        doctor = User(username="doc1", email="doc1@test.com", hashed_password=get_password_hash("docpass"), role="doctor")
        coder = User(username="code1", email="code1@test.com", hashed_password=get_password_hash("codepass"), role="coder")
        db.add(doctor)
        db.add(coder)
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_medical_workflow.db"):
            os.remove("./test_medical_workflow.db")

@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_retriever(mocker):
    return mocker.patch(
        "backend.rag.retrieval.icd_retriever.retrieve",
        return_value={
            "cm": [{
                "code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "type": "cm",
                "score": 0.85
            }],
            "pcs": []
        }
    )

def test_run_workflow_direct(db_session):
    from backend.workflows.orchestrator import run_coding_workflow
    from backend.db.models import ClinicalNote
    note = ClinicalNote(doctor_id=1, content="Patient reports historical history of diabetes.", status="pending")
    db_session.add(note)
    db_session.commit()
    run_coding_workflow(note.id, db_session)
    assert note.status == "reviewed"

def test_workflow_and_approvals(client):
    # 1. Login doctor to submit a note
    response = client.post("/api/auth/token", data={"username": "doc1", "password": "docpass"})
    assert response.status_code == 200
    doc_token = response.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Submit clinical note (contains 'diabetes' keyword)
    response = client.post("/api/coding/notes", json={
        "content": "Patient reports historical history of diabetes."
    }, headers=doc_headers)
    assert response.status_code == 201
    note = response.json()
    note_id = note["id"]
    assert note["status"] == "reviewed" # Workflow automatically runs and sets it to reviewed

    # 2. Login coder to review suggestions
    response = client.post("/api/auth/token", data={"username": "code1", "password": "codepass"})
    assert response.status_code == 200
    coder_token = response.json()["access_token"]
    coder_headers = {"Authorization": f"Bearer {coder_token}"}

    # Fetch suggestions
    response = client.get(f"/api/coding/notes/{note_id}/ai-suggestions", headers=coder_headers)
    assert response.status_code == 200
    suggestions = response.json()
    assert len(suggestions["ai_suggested_codes"]) > 0
    suggested_code = suggestions["ai_suggested_codes"][0]["code"]
    assert suggested_code == "E11.9" # Matches keyword router mock code

    # Coder approves suggestions with edits (approves E11.9)
    response = client.post("/api/coding/approvals", json={
        "coding_result_id": suggestions["id"],
        "final_codes": [
            {
                "code": "E11.9",
                "description": "Type 2 diabetes mellitus without complications",
                "type": "cm",
                "score": 0.95
            }
        ]
    }, headers=coder_headers)
    assert response.status_code == 200
    approval = response.json()
    assert approval["final_codes"][0]["code"] == "E11.9"

    # 3. Doctor checks finalized codes
    response = client.get(f"/api/coding/notes/{note_id}/final", headers=doc_headers)
    assert response.status_code == 200
    final = response.json()
    assert final["final_codes"][0]["code"] == "E11.9"
