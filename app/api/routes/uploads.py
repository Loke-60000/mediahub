from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Form
from fastapi.responses import JSONResponse
import os
import uuid
import shutil
from typing import Optional
import mimetypes
import logging
from datetime import datetime

from app.api.dependencies import get_current_user
from app.models.schema import DownloadInfo, DownloadStatus
from app.config import settings
from app.services.downloader import download_tasks

router = APIRouter()
logger = logging.getLogger("upload_routes")

@router.post("/upload", response_model=DownloadInfo)
async def upload_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    _: bool = Depends(get_current_user)
):
    """
    Upload a file to the server.
    The file will be processed as if it were downloaded from a URL.
    """
    try:
        download_id = str(uuid.uuid4())
        
        original_filename = file.filename
        _, ext = os.path.splitext(original_filename)
        safe_filename = f"{download_id}_{title or 'uploaded'}{ext}"
        file_path = os.path.join(settings.TEMP_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        content_type = file.content_type or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        
        file_size = os.path.getsize(file_path)
        
        download_info = DownloadInfo(
            download_id=download_id,
            url=f"local://{original_filename}",
            status=DownloadStatus.COMPLETED,
            progress=100.0,
            filename=file_path,
            format_id=None,
            created_at=datetime.now(),
            completed_at=datetime.now(),
            title=title or original_filename,
            thumbnail=None,
            filesize=file_size,
            content_type=content_type
        )
        

        download_tasks[download_id] = download_info
        
        logger.info(f"File uploaded successfully: {safe_filename}, size: {file_size}")
        
        return download_info
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )

@router.get("/mime-types", response_model=dict)
async def get_mime_types(
    _: bool = Depends(get_current_user)
):
    """
    Get a list of common file extensions and their MIME types.
    """
    common_types = {

        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'svg': 'image/svg+xml',
        

        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'm4a': 'audio/mp4',
        'aac': 'audio/aac',
        

        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'mkv': 'video/x-matroska',
        'avi': 'video/x-msvideo',
        'mov': 'video/quicktime',
        'flv': 'video/x-flv',
        

        'pdf': 'application/pdf',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'html': 'text/html',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    }
    
    return {"mime_types": common_types}