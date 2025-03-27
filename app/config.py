import os
import secrets
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "YouTube Downloader API"
    VERSION: str = "1.0.0"

    API_KEY: str = os.environ.get("API_KEY", secrets.token_urlsafe(32))
    REQUIRE_API_KEY: bool = os.environ.get("REQUIRE_API_KEY", "false").lower() == "true"

    ENABLE_RATE_LIMITING: bool = (
        os.environ.get("ENABLE_RATE_LIMITING", "true").lower() == "true"
    )
    RATE_LIMIT_REQUESTS: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "30"))

    CORS_ORIGINS: List[str] = os.environ.get("CORS_ORIGINS", "*").split(",")

    TEMP_DIR: str = os.environ.get("TEMP_DIR", "/tmp/youtube-dl")
    MAX_CONCURRENT_DOWNLOADS: int = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "3"))
    DOWNLOAD_TIMEOUT: int = int(
        os.environ.get("DOWNLOAD_TIMEOUT", "3600")
    )  # 1 hour timeout
    MAX_FILE_SIZE_MB: int = int(
        os.environ.get("MAX_FILE_SIZE_MB", "1000")
    )  # 1GB max file size
    QUEUE_MAX_SIZE: int = int(os.environ.get("QUEUE_MAX_SIZE", "100"))

    ENABLE_CONVERSION: bool = (
        os.environ.get("ENABLE_CONVERSION", "true").lower() == "true"
    )
    MAX_CONVERSION_SIZE_MB: int = int(os.environ.get("MAX_CONVERSION_SIZE_MB", "500"))
    CONVERSION_TIMEOUT: int = int(
        os.environ.get("CONVERSION_TIMEOUT", "600")
    )  # 10 minutes timeout
    DEFAULT_IMAGE_QUALITY: int = int(os.environ.get("DEFAULT_IMAGE_QUALITY", "90"))
    FFMPEG_PATH: str = os.environ.get("FFMPEG_PATH", "ffmpeg")
    IMAGEMAGICK_PATH: str = os.environ.get("IMAGEMAGICK_PATH", "convert")

    @classmethod
    def setup_temp_dir(cls):
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        return cls.TEMP_DIR


settings = Settings()
