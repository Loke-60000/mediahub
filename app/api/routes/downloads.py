from fastapi import APIRouter, Depends, HTTPException, status, Response, Body
from fastapi.responses import FileResponse
import asyncio
import os
import logging
from typing import List
import yt_dlp
from app.models.schema import DownloadInfo, DownloadRequest, DownloadStatus, StreamSelectionMode
from app.api.dependencies import get_current_user
from app.services.downloader import (
    start_download,
    get_download_info,
    delete_download,
    download_tasks,
    download_queue,
)
from app.core.errors import NotFoundError, QueueFullError

router = APIRouter()
logger = logging.getLogger("download_routes")

@router.post("/download", response_model=DownloadInfo)
async def create_download(
    request: DownloadRequest, _: bool = Depends(get_current_user)
):
    """
    Start a new download process.
    """
    try:
        if download_queue.full():
            raise QueueFullError()
        download_info = await start_download(
            str(request.url),
            request.format_id,
            request.stream_selection_mode
        )
        return download_info
    except asyncio.QueueFull:
        raise QueueFullError()
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error with the video URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start download: {str(e)}"
        )

@router.post("/youtube", response_model=DownloadInfo)
async def youtube_download(
    url: str = Body(..., description="YouTube URL"),
    quality: str = Body("best", description="Quality preset (best, 1080p, 720p, 480p, 360p, audio)"),
    mode: StreamSelectionMode = Body(StreamSelectionMode.VIDEO_AUDIO, description="Download mode"),
    _: bool = Depends(get_current_user)
):
    """
    Simplified YouTube download endpoint.
    - url: YouTube video URL
    - quality: Quality preset (best, 1080p, 720p, 480p, 360p, audio)
    - mode: Download mode (video+audio, video-only, audio-only)
    """
    try:
        if download_queue.full():
            raise QueueFullError()
        format_selector = None
        if mode == StreamSelectionMode.AUDIO_ONLY:
            format_selector = "bestaudio/best"
        elif quality == "best":
            format_selector = "bestvideo+bestaudio/best" if mode == StreamSelectionMode.VIDEO_AUDIO else "bestvideo/best"
        elif quality == "1080p":
            format_selector = "bestvideo[height<=1080]+bestaudio/best[height<=1080]" if mode == StreamSelectionMode.VIDEO_AUDIO else "bestvideo[height<=1080]/best[height<=1080]"
        elif quality == "720p":
            format_selector = "bestvideo[height<=720]+bestaudio/best[height<=720]" if mode == StreamSelectionMode.VIDEO_AUDIO else "bestvideo[height<=720]/best[height<=720]"
        elif quality == "480p":
            format_selector = "bestvideo[height<=480]+bestaudio/best[height<=480]" if mode == StreamSelectionMode.VIDEO_AUDIO else "bestvideo[height<=480]/best[height<=480]"
        elif quality == "360p":
            format_selector = "bestvideo[height<=360]+bestaudio/best[height<=360]" if mode == StreamSelectionMode.VIDEO_AUDIO else "bestvideo[height<=360]/best[height<=360]"
        elif quality == "audio":
            format_selector = "bestaudio/best"
            mode = StreamSelectionMode.AUDIO_ONLY
        else:
            format_selector = "best"
        download_info = await start_download(
            str(url),
            format_selector,
            mode
        )
        return download_info
    except asyncio.QueueFull:
        raise QueueFullError()
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error with the video URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start download: {str(e)}"
        )

@router.get("/status/{download_id}", response_model=DownloadInfo)
async def get_download_status(download_id: str, _: bool = Depends(get_current_user)):
    """
    Get the status of a download.
    """
    download_info = get_download_info(download_id)
    if not download_info:
        raise NotFoundError("Download", download_id)
    return download_info

@router.get("/{download_id}")
async def download_file(download_id: str, _: bool = Depends(get_current_user)):
    """
    Download a completed file.
    """
    logger.info(f"Download request received for ID: {download_id}")
    download_info = get_download_info(download_id)
    if not download_info:
        logger.error(f"Download not found: {download_id}")
        raise NotFoundError("Download", download_id)
        
    if download_info.status != DownloadStatus.COMPLETED:
        logger.error(f"Download not completed. Status: {download_info.status}")
        raise HTTPException(
            status_code=400,
            detail=f"Download is not completed. Status: {download_info.status}",
        )
        

    if not download_info.filename:
        logger.error(f"Filename not available for download: {download_id}")
        raise HTTPException(status_code=404, detail="Filename not available for this download")
        
    logger.info(f"Attempting to serve file: {download_info.filename}")
    
    if not os.path.exists(download_info.filename):
        logger.error(f"File not found: {download_info.filename}")

        try:
            temp_dir = os.path.dirname(download_info.filename)
            files = os.listdir(temp_dir)
            matching_files = [f for f in files if download_id in f]
            logger.info(f"Files in directory matching download ID: {matching_files}")
            
            if matching_files:

                corrected_filename = os.path.join(temp_dir, matching_files[0])
                logger.info(f"Using alternative found file: {corrected_filename}")
                download_info.filename = corrected_filename

                download_tasks[download_id] = download_info
                

                return FileResponse(
                    path=corrected_filename,
                    filename=os.path.basename(corrected_filename),
                    media_type=download_info.content_type or "application/octet-stream",
                )
        except Exception as e:
            logger.error(f"Error while searching for file alternatives: {str(e)}")
            
        raise HTTPException(status_code=404, detail=f"File not found on server: {os.path.basename(download_info.filename)}")
        
    logger.info(f"Serving file: {download_info.filename}")
    return FileResponse(
        path=download_info.filename,
        filename=os.path.basename(download_info.filename),
        media_type=download_info.content_type or "application/octet-stream",
    )

@router.get("/downloads", response_model=List[DownloadInfo])
async def list_downloads(_: bool = Depends(get_current_user)):
    """
    List all downloads.
    """
    return list(download_tasks.values())

@router.delete("/{download_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_download(download_id: str, _: bool = Depends(get_current_user)):
    """
    Delete a download and its associated file.
    """
    if not delete_download(download_id):
        raise NotFoundError("Download", download_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)