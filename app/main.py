import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import info, downloads, conversion, uploads
from app.services.downloader import lifespan_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("app.log")],
)
logger = logging.getLogger("app")

settings.setup_temp_dir()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for downloading videos from YouTube and other platforms with conversion capabilities",
    version=settings.VERSION,
    lifespan=lifespan_context,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(info.router, tags=["info"])
app.include_router(downloads.router, tags=["downloads"])
app.include_router(downloads.router, prefix="/download", include_in_schema=False)
app.include_router(conversion.router, prefix="/conversion", tags=["conversion"])
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])


@app.get("/")
async def root():
    return {
        "message": "YouTube Downloader & Conversion API is running",
        "version": settings.VERSION,
        "docs_url": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port, reload=False, log_level="info")
