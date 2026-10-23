
from fastapi import FastAPI

app = FastAPI(
    title="Pramaan AI API",
    description="AI-powered regulatory document validation and compliance support",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Welcome to Pramaan AI",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Pramaan AI API",
    }
