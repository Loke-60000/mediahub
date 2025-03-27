# app/models/schema.py

from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, HttpUrl

# --- Define Enums First ---

class FormatType(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    VIDEO_AUDIO = "video+audio"

class DownloadStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"

class StreamSelectionMode(str, Enum):
    VIDEO_AUDIO = "video+audio"  # Default, both video and audio
    VIDEO_ONLY = "video-only"    # Video stream only, no audio
    AUDIO_ONLY = "audio-only"    # Audio stream only, no video

# --- Define Models ---

class VideoFormat(BaseModel):
    format_id: str
    format_note: Optional[str] = None
    ext: str
    resolution: Optional[str] = None
    fps: Optional[float] = None
    filesize: Optional[int] = None
    format_type: FormatType = FormatType.VIDEO

class VideoInfo(BaseModel):
    video_id: str
    title: str
    formats: List[VideoFormat]
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    description: Optional[str] = None
    uploader: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None

class DownloadRequest(BaseModel):
    url: HttpUrl
    format_id: Optional[str] = None
    quality: Optional[str] = None
    stream_selection_mode: Optional[StreamSelectionMode] = None # Now StreamSelectionMode is defined

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "format_id": "22",
                "quality": "720p",
                "stream_selection_mode": "video+audio"
            }
        }
    }

class DownloadInfo(BaseModel):
    download_id: str
    url: str
    status: DownloadStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    filename: Optional[str] = None
    format_id: Optional[str] = None
    stream_selection_mode: Optional[StreamSelectionMode] = None # Now StreamSelectionMode is defined
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None # Note: This might not be used if files are deleted quickly
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    filesize: Optional[int] = None
    content_type: Optional[str] = None

class SystemStatus(BaseModel):
    active_downloads: int
    queued_downloads: int
    completed_downloads: int
    failed_downloads: int
    total_downloads: int
    disk_usage_percent: float
    queue_utilization_percent: float
    uptime_seconds: float
    version: str