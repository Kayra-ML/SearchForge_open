import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.search import router as search_router
from app.api.documents import router as documents_router
from app.api.index import router as index_router
from app.services.drive_service import check_drive_connection
from app.services.index_service import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

settings = get_settings()

app = FastAPI(
    title="SearchForge API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(search_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(index_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/api/health")
async def health():
    drive_ok = check_drive_connection()
    return {
        "status": "ok" if drive_ok else "degraded",
        "drive": "connected" if drive_ok else "disconnected",
    }


@app.get("/")
async def root():
    return {"message": "SearchForge API is running"}