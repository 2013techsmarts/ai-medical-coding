from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db.database import engine, Base
from .auth.router import router as auth_router
from .api.router import router as coding_router
from .config.config import settings

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(coding_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Medical Coding API", "status": "healthy"}
