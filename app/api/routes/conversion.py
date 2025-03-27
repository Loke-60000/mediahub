from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from fastapi.responses import FileResponse
import os
import asyncio
import logging
from typing import List, Optional

from app.models.conversion import (
    ConversionRequest,
    ConversionInfo,
    ConversionStatus,
    AvailableFormats,
)
from app.api.dependencies import get_current_user
from app.services.converter import (
    start_conversion,
    get_conversion_info,
    delete_conversion,
    conversion_tasks,
    conversion_queue,
    get_available_formats,
)
from app.core.errors import NotFoundError, QueueFullError

router = APIRouter()
logger = logging.getLogger("conversion_routes")


@router.get("/formats", response_model=AvailableFormats)
async def list_formats(_: bool = Depends(get_current_user)):
    """
    Get all available conversion formats
    """
    return get_available_formats()


@router.post("/convert", response_model=ConversionInfo)
async def convert_file(request: ConversionRequest, _: bool = Depends(get_current_user)):
    """
    Convert a file to a different format
    """
    try:
        if not request.source_url and not request.download_id:
            raise HTTPException(
                status_code=400,
                detail="Either source_url or download_id must be provided",
            )

        if conversion_queue.full():
            raise QueueFullError()

        conversion_info = await start_conversion(request.dict())
        return conversion_info

    except asyncio.QueueFull:
        raise QueueFullError()
    except Exception as e:
        logger.error(f"Error starting conversion: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start conversion: {str(e)}"
        )


@router.get("/convert/{conversion_id}", response_model=ConversionInfo)
async def get_conversion_status(
    conversion_id: str, _: bool = Depends(get_current_user)
):
    """
    Get the status of a conversion
    """
    conversion_info = get_conversion_info(conversion_id)
    if not conversion_info:
        raise NotFoundError("Conversion", conversion_id)
    return conversion_info


@router.get("/download-conversion/{conversion_id}")
async def download_converted_file(
    conversion_id: str, _: bool = Depends(get_current_user)
):
    """
    Download a completed converted file
    """
    conversion_info = get_conversion_info(conversion_id)
    if not conversion_info:
        raise NotFoundError("Conversion", conversion_id)

    if conversion_info.status != ConversionStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Conversion is not completed. Status: {conversion_info.status}",
        )

    if not conversion_info.filename or not os.path.exists(conversion_info.filename):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path=conversion_info.filename,
        filename=os.path.basename(conversion_info.filename),
        media_type=conversion_info.content_type or "application/octet-stream",
    )


@router.get("/conversions", response_model=List[ConversionInfo])
async def list_conversions(_: bool = Depends(get_current_user)):
    """
    List all conversions
    """
    return list(conversion_tasks.values())


@router.delete("/convert/{conversion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_conversion(conversion_id: str, _: bool = Depends(get_current_user)):
    """
    Delete a conversion and its associated file
    """
    if not delete_conversion(conversion_id):
        raise NotFoundError("Conversion", conversion_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
