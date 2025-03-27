from fastapi import APIRouter, Depends, HTTPException, Query
import logging
import yt_dlp
from typing import List

from app.models.schema import VideoInfo, FormatType, VideoFormat
from app.api.dependencies import get_current_user
from app.services.downloader import get_system_stats

router = APIRouter()
logger = logging.getLogger("info_routes")


@router.get("/", response_model=dict)
async def root():
    """
    API root endpoint returns basic information.
    """
    return {
        "message": "Video Downloader API is running",
        "version": "1.0.0",
        "docs_url": "/docs",
        "status_url": "/status",
    }


@router.get("/status", response_model=dict)
async def system_status(_: bool = Depends(get_current_user)):
    """
    Get current system status and statistics.
    """
    return get_system_stats().dict()


@router.get("/info", response_model=VideoInfo)
async def get_video_info(
    url: str = Query(..., description="URL of the video"),
    _: bool = Depends(get_current_user),
):
    """
    Extract information about a video without downloading it.
    """
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            processed_formats = []
            for fmt in info.get("formats", []):
                format_type = FormatType.VIDEO_AUDIO
                if fmt.get("vcodec", "none") == "none":
                    format_type = FormatType.AUDIO
                elif fmt.get("acodec", "none") == "none":
                    format_type = FormatType.VIDEO

                resolution = None
                if fmt.get("width") and fmt.get("height"):
                    resolution = f"{fmt.get('width')}x{fmt.get('height')}"

                processed_formats.append(
                    VideoFormat(
                        format_id=fmt.get("format_id", ""),
                        format_note=fmt.get("format_note"),
                        ext=fmt.get("ext", ""),
                        resolution=resolution,
                        fps=fmt.get("fps"),
                        filesize=fmt.get("filesize"),
                        format_type=format_type,
                    )
                )

            return VideoInfo(
                video_id=info.get("id", ""),
                title=info.get("title", ""),
                formats=processed_formats,
                duration=info.get("duration"),
                thumbnail=info.get("thumbnail"),
                description=info.get("description"),
                uploader=info.get("uploader"),
                upload_date=info.get("upload_date"),
                view_count=info.get("view_count"),
            )
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp error: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Error fetching video info: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting info: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get video info: {str(e)}"
        )
