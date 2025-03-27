import os
import uuid
import asyncio
import subprocess
import logging
import time
import traceback
from datetime import datetime
from typing import Dict, Optional, Any
import mimetypes
import shutil
from app.models.conversion import ConversionInfo, ConversionStatus
from app.services.formats import (
    get_media_type,
    get_mime_type,
    get_conversion_command,
    can_convert,
    ALL_FORMATS,
)
from app.config import settings
from app.services.downloader import get_download_info

logger = logging.getLogger("converter")

conversion_tasks: Dict[str, ConversionInfo] = {}
conversion_queue = asyncio.Queue(maxsize=settings.QUEUE_MAX_SIZE)
conversion_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_DOWNLOADS // 2)


async def conversion_worker():
    """
    Background worker that processes conversion requests from the queue
    """
    while True:
        try:
            conversion_id = await conversion_queue.get()
            if conversion_id not in conversion_tasks:
                conversion_queue.task_done()
                continue
            conversion_info = conversion_tasks[conversion_id]
            conversion_info.status = ConversionStatus.PROCESSING
            try:
                source_path = None
                if conversion_info.download_id:
                    download_info = get_download_info(conversion_info.download_id)
                    if download_info and download_info.filename:
                        source_path = download_info.filename
                elif conversion_info.source_url:
                    # TODO:
                    pass
                if not source_path or not os.path.exists(source_path):
                    raise FileNotFoundError("Source file not found")
                file_size = os.path.getsize(source_path)
                if file_size > settings.MAX_CONVERSION_SIZE_MB * 1024 * 1024:
                    raise ValueError(
                        f"File too large for conversion (max: {settings.MAX_CONVERSION_SIZE_MB} MB)"
                    )
                source_ext = os.path.splitext(source_path)[1].lower().lstrip(".")
                source_type = get_media_type(source_path)
                if not source_type:
                    raise ValueError(f"Unsupported source file format: {source_ext}")
                target_ext = conversion_info.output_format.lower()
                if not can_convert(source_type, source_ext, target_ext):
                    raise ValueError(
                        f"Conversion from {source_ext} to {target_ext} is not supported"
                    )
                output_filename = f"{conversion_id}_{os.path.splitext(os.path.basename(source_path))[0]}.{target_ext}"
                output_path = os.path.join(settings.TEMP_DIR, output_filename)
                options = {
                    "preserve_transparency": True,
                    "quality": settings.DEFAULT_IMAGE_QUALITY,
                }

                # Get the command and log it for debugging
                command = get_conversion_command(source_path, output_path, options)
                cmd_str = " ".join(command)
                logger.info(f"Starting conversion: {cmd_str}")

                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=settings.CONVERSION_TIMEOUT
                    )
                    if process.returncode != 0:
                        error_msg = (
                            stderr.decode() if stderr else "Unknown conversion error"
                        )
                        logger.error(f"Conversion failed: {error_msg}")
                        raise RuntimeError(f"Conversion failed: {error_msg}")
                    conversion_info.status = ConversionStatus.COMPLETED
                    conversion_info.filename = output_path
                    conversion_info.completed_at = datetime.now().isoformat()
                    mime_type = (
                        get_mime_type(target_ext)
                        or mimetypes.guess_type(output_path)[0]
                    )
                    conversion_info.content_type = mime_type
                    if os.path.exists(output_path):
                        conversion_info.file_size = os.path.getsize(output_path)
                    logger.info(f"Conversion completed: {conversion_id}")
                except asyncio.TimeoutError:
                    logger.error(f"Conversion timed out: {conversion_id}")
                    if process:
                        process.kill()
                    raise TimeoutError("Conversion operation timed out")
            except Exception as e:
                logger.error(f"Conversion failed: {str(e)}")
                logger.error(traceback.format_exc())
                conversion_info.status = ConversionStatus.FAILED
                conversion_info.error = str(e)
            finally:
                conversion_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Unexpected error in conversion worker: {str(e)}")
            logger.error(traceback.format_exc())
            await asyncio.sleep(1)


async def start_conversion(request: Dict[str, Any]) -> ConversionInfo:
    """
    Start a conversion process
    """
    conversion_id = str(uuid.uuid4())
    conversion_info = ConversionInfo(
        conversion_id=conversion_id,
        status=ConversionStatus.PENDING,
        source_url=request.get("source_url"),
        download_id=request.get("download_id"),
        output_format=request.get("output_format"),
        created_at=datetime.now().isoformat(),
    )
    conversion_tasks[conversion_id] = conversion_info
    await conversion_queue.put(conversion_id)
    return conversion_info


def get_conversion_info(conversion_id: str) -> Optional[ConversionInfo]:
    """
    Get information about a specific conversion
    """
    return conversion_tasks.get(conversion_id)


def delete_conversion(conversion_id: str) -> bool:
    """
    Delete a conversion and its associated file
    """
    if conversion_id not in conversion_tasks:
        return False
    conversion_info = conversion_tasks[conversion_id]
    if conversion_info.filename and os.path.exists(conversion_info.filename):
        try:
            os.remove(conversion_info.filename)
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
    del conversion_tasks[conversion_id]
    return True


def get_available_formats():
    """
    Return all available format conversions
    """
    from app.models.conversion import AvailableFormats

    return AvailableFormats()


async def start_conversion_workers():
    """
    Start the conversion worker tasks
    """
    workers = []
    worker_count = max(1, settings.MAX_CONCURRENT_DOWNLOADS // 2)
    for i in range(worker_count):
        task = asyncio.create_task(conversion_worker())
        workers.append(task)
    logger.info(f"Started {len(workers)} conversion workers")
    return workers


async def cleanup_conversion_files():
    """
    Clean up old converted files
    """
    while True:
        try:
            now = datetime.now()
            for conversion_id, info in list(conversion_tasks.items()):
                if info.status == ConversionStatus.COMPLETED and info.completed_at:
                    completed_time = None
                    try:
                        completed_time = datetime.fromisoformat(info.completed_at)
                    except ValueError:
                        logger.error(
                            f"Invalid datetime format in conversion {conversion_id}"
                        )
                        continue
                    if (
                        completed_time
                        and (now - completed_time).total_seconds() > 30 * 60
                    ):
                        if info.filename and os.path.exists(info.filename):
                            logger.info(f"Cleaning up conversion {conversion_id}")
                            delete_conversion(conversion_id)
                        else:
                            logger.info(
                                f"Removing conversion entry (file already gone): {conversion_id}"
                            )
                            conversion_tasks.pop(conversion_id, None)
        except Exception as e:
            logger.error(f"Error in conversion cleanup: {str(e)}")
        await asyncio.sleep(600)
