from fastapi import FastAPI
from backend.database import engine
import backend.models as models
from backend.routers import auth, chat, chatbot, documents, employees, leaves

# Create all tables in MySQL if they don't exist yet
models.Base.metadata.create_all(bind=engine)

# Create the FastAPI app
app = FastAPI(
    title="HRPilot AI",
    description="API for HR automation system",
    version="1.0.0"
)

app.include_router(auth.router) 
app.include_router(employees.router)   
app.include_router(leaves.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(chatbot.router)
# ── Test route — just to verify everything works ──────────────────────────────
@app.get("/")
def root():
    return {"message": "HRPilot AI API is running ✅"}

@app.get("/health")
def health_check():
    return {"status": "ok", "database": "connected"}

