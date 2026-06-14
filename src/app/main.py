import asyncio
import logging
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.api.endpoints import router as api_router
from app.database import init_database
from app.services.usage_reset import run_usage_limit_reset_loop

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app")
usage_reset_task: asyncio.Task | None = None

app = FastAPI(
    title="Document Validator API",
    description="API для конвертации DOCX → LaTeX и проверки академических документов",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="")


@app.on_event("startup")
async def startup_event():
    global usage_reset_task
    init_database()
    usage_reset_task = asyncio.create_task(run_usage_limit_reset_loop())


@app.on_event("shutdown")
async def shutdown_event():
    if usage_reset_task is not None and not usage_reset_task.done():
        usage_reset_task.cancel()
        try:
            await usage_reset_task
        except asyncio.CancelledError:
            logger.info("Automatic usage limit reset stopped")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code >= 500:
        logger.error(
            "HTTP %s on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.detail,
        )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

@app.get("/")
async def root():
    return {
        "message": "Document Validator API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
