import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.db.database import Base, get_db
import os

# Setup temporary sqlite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_medical_coding.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_medical_coding.db"):
            os.remove("./test_medical_coding.db")

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

def test_register_user(client):
    # Test Doctor Registration
    response = client.post("/api/auth/register", json={
        "username": "testdoctor",
        "email": "doctor@test.com",
        "password": "doctorpassword",
        "role": "doctor"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "testdoctor"
    assert response.json()["role"] == "doctor"

    # Test Coder Registration
    response = client.post("/api/auth/register", json={
        "username": "testcoder",
        "email": "coder@test.com",
        "password": "coderpassword",
        "role": "coder"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "testcoder"
    assert response.json()["role"] == "coder"

def test_login_user(client):
    # Login doctor
    response = client.post("/api/auth/token", data={
        "username": "testdoctor",
        "password": "doctorpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "doctor"

    # Login with JSON
    response = client.post("/api/auth/login", json={
        "username": "testcoder",
        "password": "coderpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "coder"
