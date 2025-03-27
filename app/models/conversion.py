from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class ImageFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    JPG = "jpg"
    WEBP = "webp"
    GIF = "gif"
    BMP = "bmp"
    TIFF = "tiff"
    ICO = "ico"
    SVG = "svg"


class VideoFormat(str, Enum):
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"
    AVI = "avi"
    MOV = "mov"
    FLV = "flv"
    GIF = "gif"


class AudioFormat(str, Enum):
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    AAC = "aac"
    FLAC = "flac"
    M4A = "m4a"


class DocumentFormat(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    HTML = "html"


class ResizeMode(str, Enum):
    FIT = "fit"
    FILL = "fill"
    STRETCH = "stretch"


class ConversionRequest(BaseModel):
    source_url: Optional[HttpUrl] = None
    download_id: Optional[str] = None
    output_format: str
    preserve_transparency: bool = True


    width: Optional[int] = None
    height: Optional[int] = None
    quality: Optional[int] = Field(None, ge=1, le=100)
    resize_mode: Optional[ResizeMode] = ResizeMode.FIT


    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    video_bitrate: Optional[str] = None
    audio_bitrate: Optional[str] = None
    fps: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "download_id": "123e4567-e89b-12d3-a456-426614174000",
                "output_format": "png",
                "preserve_transparency": True,
                "width": 800,
                "height": 600,
                "quality": 90,
                "resize_mode": "fit",
            }
        }
    }


class ConversionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionInfo(BaseModel):
    conversion_id: str
    status: ConversionStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    source_url: Optional[str] = None
    download_id: Optional[str] = None
    output_format: str
    filename: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None


class AvailableFormats(BaseModel):
    image: List[str] = Field(default_factory=lambda: [f.value for f in ImageFormat])
    video: List[str] = Field(default_factory=lambda: [f.value for f in VideoFormat])
    audio: List[str] = Field(default_factory=lambda: [f.value for f in AudioFormat])
    document: List[str] = Field(
        default_factory=lambda: [f.value for f in DocumentFormat]
    )
