import asyncio
import os
import uuid
import yt_dlp
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any, List, Union
from contextlib import asynccontextmanager
from app.models.schema import DownloadInfo, DownloadStatus, StreamSelectionMode
from app.config import settings

logger = logging.getLogger("downloader")

download_tasks: Dict[str, DownloadInfo] = {}
download_queue = asyncio.Queue(maxsize=settings.QUEUE_MAX_SIZE)
download_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_DOWNLOADS)
app_start_time = time.time()


def progress_hook(download_id: str) -> Callable:
    """
    Creates a progress hook for yt-dlp.
    """

    def hook(d):
        if download_id not in download_tasks:
            return
        if d["status"] == "downloading":
            if "total_bytes" in d and d["total_bytes"] > 0:
                progress = d["downloaded_bytes"] / d["total_bytes"] * 100
            elif "total_bytes_estimate" in d and d["total_bytes_estimate"] > 0:
                progress = d["downloaded_bytes"] / d["total_bytes_estimate"] * 100
            else:
                progress = 0
            if "total_bytes" in d:
                download_tasks[download_id].filesize = d["total_bytes"]
            elif "total_bytes_estimate" in d:
                download_tasks[download_id].filesize = d["total_bytes_estimate"]
            download_tasks[download_id].progress = min(99.0, progress)
        elif d["status"] == "finished":
            download_tasks[download_id].status = DownloadStatus.PROCESSING
            download_tasks[download_id].progress = 99.5
            download_tasks[download_id].filename = d.get("filename", None)

    return hook


async def download_worker():
    """
    Worker task for processing download queue items.
    """
    while True:
        try:
            download_id = await download_queue.get()
            if download_id not in download_tasks:
                download_queue.task_done()
                continue
            download_info = download_tasks[download_id]
            download_timeout = asyncio.create_task(
                asyncio.sleep(settings.DOWNLOAD_TIMEOUT)
            )
            download_task = None
            try:
                async with download_semaphore:
                    download_info.status = DownloadStatus.DOWNLOADING
                    output_template = os.path.join(
                        settings.TEMP_DIR, f"{download_id}_%(title)s.%(ext)s"
                    )

                    format_spec = download_info.format_id
                    post_processors = []

                    target_video_format = "mp4"
                    target_audio_format = "mp3"

                    if format_spec:
                        pass
                    elif download_info.stream_selection_mode:
                        if (
                            download_info.stream_selection_mode
                            == StreamSelectionMode.VIDEO_ONLY
                        ):
                            format_spec = "bestvideo"
                            post_processors.append(
                                {
                                    "key": "FFmpegVideoConvertor",
                                    "preferedformat": target_video_format,
                                }
                            )
                        elif (
                            download_info.stream_selection_mode
                            == StreamSelectionMode.AUDIO_ONLY
                        ):
                            format_spec = "bestaudio"
                            post_processors.append(
                                {
                                    "key": "FFmpegExtractAudio",
                                    "preferredcodec": target_audio_format,
                                    "preferredquality": "192",
                                }
                            )
                        elif (
                            download_info.stream_selection_mode
                            == StreamSelectionMode.VIDEO_AUDIO
                        ):
                            format_spec = "bestvideo+bestaudio/best"
                            post_processors.append(
                                {
                                    "key": "FFmpegVideoConvertor",
                                    "preferedformat": target_video_format,
                                }
                            )
                    if not format_spec:
                        format_spec = "best"
                        post_processors.append(
                            {
                                "key": "FFmpegVideoConvertor",
                                "preferedformat": target_video_format,
                            }
                        )

                    logger.info(f"Using format specification: {format_spec}")
                    ydl_opts = {
                        "format": format_spec,
                        "outtmpl": output_template,
                        "progress_hooks": [progress_hook(download_id)],
                        "quiet": True,
                        "noplaylist": True,
                        "restrictfilenames": True,
                        "max_filesize": settings.MAX_FILE_SIZE_MB * 1024 * 1024,
                    }

                    if post_processors:
                        ydl_opts["postprocessors"] = post_processors

                    logger.info(f"Download options: {ydl_opts}")
                    logger.info(f"Starting download for {download_info.url}")

                    download_task = asyncio.create_task(
                        asyncio.to_thread(
                            lambda: yt_dlp.YoutubeDL(ydl_opts).download(
                                [download_info.url]
                            )
                        )
                    )
                    done, pending = await asyncio.wait(
                        [download_task, download_timeout],
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                    if download_timeout in done:
                        raise TimeoutError("Download operation timed out")
                    if download_id in download_tasks:
                        download_tasks[download_id].status = DownloadStatus.COMPLETED
                        download_tasks[download_id].completed_at = datetime.now()
                        download_tasks[download_id].progress = 100.0

                        if download_tasks[download_id].filename:
                            filename = download_tasks[download_id].filename
                            if not os.path.exists(filename):
                                temp_dir = os.path.dirname(filename)
                                if os.path.exists(temp_dir):
                                    all_files = os.listdir(temp_dir)

                                    expected_ext = (
                                        ".mp3"
                                        if download_info.stream_selection_mode
                                        == StreamSelectionMode.AUDIO_ONLY
                                        else ".mp4"
                                    )
                                    matching_files_with_ext = [
                                        f
                                        for f in all_files
                                        if download_id in f and f.endswith(expected_ext)
                                    ]

                                    if matching_files_with_ext:
                                        download_tasks[download_id].filename = (
                                            os.path.join(
                                                temp_dir, matching_files_with_ext[0]
                                            )
                                        )
                                        filename = download_tasks[download_id].filename
                                        logger.info(
                                            f"Updated download filename to match expected extension: {filename}"
                                        )
                                    else:
                                        matching_files = [
                                            f for f in all_files if download_id in f
                                        ]
                                        if matching_files:
                                            download_tasks[download_id].filename = (
                                                os.path.join(
                                                    temp_dir, matching_files[0]
                                                )
                                            )
                                            filename = download_tasks[
                                                download_id
                                            ].filename
                                            logger.info(
                                                f"Updated download filename: {filename}"
                                            )

                            ext = os.path.splitext(filename)[1].lower()

                            if ext in [".mp4", ".webm", ".mkv", ".avi", ".mov"]:
                                download_tasks[download_id].content_type = (
                                    f"video/{ext[1:]}"
                                )
                            elif ext in [".mp3", ".wav", ".aac", ".flac", ".ogg"]:
                                download_tasks[download_id].content_type = (
                                    f"audio/{ext[1:]}"
                                )
                            else:
                                download_tasks[download_id].content_type = (
                                    "application/octet-stream"
                                )

                            final_size = (
                                os.path.getsize(filename)
                                if os.path.exists(filename)
                                else 0
                            )
                            logger.info(
                                f"Final file: {filename}, size: {final_size}, type: {download_tasks[download_id].content_type}"
                            )
                    logger.info(f"Download completed for {download_id}")
            except asyncio.CancelledError:
                logger.warning(f"Download {download_id} was cancelled")
                if download_id in download_tasks:
                    download_tasks[download_id].status = DownloadStatus.CANCELED
                    download_tasks[download_id].error = "Download was cancelled"
            except TimeoutError:
                logger.error(f"Download {download_id} timed out")
                if download_id in download_tasks:
                    download_tasks[download_id].status = DownloadStatus.FAILED
                    download_tasks[download_id].error = "Download operation timed out"
            except Exception as e:
                logger.error(f"Download failed for {download_id}: {str(e)}")
                if download_id in download_tasks:
                    download_tasks[download_id].status = DownloadStatus.FAILED
                    download_tasks[download_id].error = str(e)
            finally:
                download_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Unexpected error in download worker: {str(e)}")
            await asyncio.sleep(1)


@asynccontextmanager
async def lifespan_context(app: Any = None):
    """Context manager for setting up and tearing down download workers"""
    workers = []
    for i in range(settings.MAX_CONCURRENT_DOWNLOADS):
        task = asyncio.create_task(download_worker())
        workers.append(task)
    from app.services.cleanup import cleanup_task

    cleanup = asyncio.create_task(cleanup_task())
    from app.services.converter import (
        start_conversion_workers,
        cleanup_conversion_files,
    )

    conversion_workers = await start_conversion_workers()
    conversion_cleanup = asyncio.create_task(cleanup_conversion_files())
    logger.info(
        f"Application started with {settings.MAX_CONCURRENT_DOWNLOADS} download workers"
    )
    yield
    logger.info("Shutting down application, cancelling tasks...")
    cleanup.cancel()
    conversion_cleanup.cancel()
    for task in workers + conversion_workers:
        task.cancel()
    try:
        await asyncio.gather(
            *workers,
            *conversion_workers,
            cleanup,
            conversion_cleanup,
            return_exceptions=True,
        )
    except asyncio.CancelledError:
        pass
    logger.info("All tasks cancelled successfully")


async def get_video_info(url: str):
    """
    Extract information about a video without downloading it.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


async def start_download(
    url: str,
    format_id: Optional[str] = None,
    stream_selection_mode: Optional[StreamSelectionMode] = None,
):
    """
    Start a new download process.
    """
    info = await get_video_info(url)
    download_id = str(uuid.uuid4())
    download_info = DownloadInfo(
        download_id=download_id,
        url=url,
        status=DownloadStatus.QUEUED,
        format_id=format_id,
        stream_selection_mode=stream_selection_mode,
        created_at=datetime.now(),
        title=info.get("title"),
        thumbnail=info.get("thumbnail"),
    )
    download_tasks[download_id] = download_info
    await download_queue.put(download_id)
    return download_info


def get_download_info(download_id: str) -> Optional[DownloadInfo]:
    """
    Get information about a specific download.
    """
    return download_tasks.get(download_id)


def delete_download(download_id: str) -> bool:
    """
    Delete a download and its associated file.
    """
    if download_id not in download_tasks:
        return False
    download_info = download_tasks[download_id]
    if download_info.filename and os.path.exists(download_info.filename):
        try:
            os.remove(download_info.filename)
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
    del download_tasks[download_id]
    return True


def get_system_stats():
    """
    Get the current system statistics.
    """
    from app.models.schema import SystemStatus
    import shutil

    active_downloads = len(
        [
            d
            for d in download_tasks.values()
            if d.status in (DownloadStatus.DOWNLOADING, DownloadStatus.PROCESSING)
        ]
    )
    queued_downloads = len(
        [d for d in download_tasks.values() if d.status == DownloadStatus.QUEUED]
    )
    completed_downloads = len(
        [d for d in download_tasks.values() if d.status == DownloadStatus.COMPLETED]
    )
    failed_downloads = len(
        [
            d
            for d in download_tasks.values()
            if d.status in (DownloadStatus.FAILED, DownloadStatus.CANCELED)
        ]
    )
    if os.path.exists(settings.TEMP_DIR):
        disk_usage = shutil.disk_usage(settings.TEMP_DIR)
        disk_usage_percent = (disk_usage.used / disk_usage.total) * 100
    else:
        disk_usage_percent = 0.0
    return SystemStatus(
        active_downloads=active_downloads,
        queued_downloads=queued_downloads,
        completed_downloads=completed_downloads,
        failed_downloads=failed_downloads,
        total_downloads=len(download_tasks),
        disk_usage_percent=disk_usage_percent,
        queue_utilization_percent=(download_queue.qsize() / settings.QUEUE_MAX_SIZE)
        * 100,
        uptime_seconds=time.time() - app_start_time,
        version=settings.VERSION,
    )


def get_download_formats(video_info: Dict) -> Dict[str, List[Dict]]:
    """
    Organizes formats from a video into categories for easier selection.
    Returns:
        Dict with keys 'video_audio', 'video_only', and 'audio_only'
    """
    formats = video_info.get("formats", [])
    result = {
        "video_audio": [],
        "video_only": [],
        "audio_only": [],
    }
    for fmt in formats:
        has_video = fmt.get("vcodec", "none") != "none"
        has_audio = fmt.get("acodec", "none") != "none"
        if has_video and has_audio:
            result["video_audio"].append(fmt)
        elif has_video:
            result["video_only"].append(fmt)
        elif has_audio:
            result["audio_only"].append(fmt)
    return result
