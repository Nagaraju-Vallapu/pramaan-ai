
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import applications_router, auth_router, documents_router, review_router
from app.core.config import FRONTEND_ORIGINS
from app.core.database import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("PRAMAAN_TESTING") != "1":
        initialize_database()
    yield


app = FastAPI(
    title="Pramaan AI API",
    description=(
        "Local MVP for document processing and illustrative compliance checks. "
        "Issuer verification uses synthetic data only; this service does not approve institutions."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_origin_regex=r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(applications_router)
app.include_router(documents_router)
app.include_router(review_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Pramaan AI",
        "status": "running",
        "environment": "local-mvp",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Pramaan AI API",
    }
