import asyncio
import os
import logging
from datetime import datetime, timedelta
from app.config import settings
from app.services.downloader import download_tasks

logger = logging.getLogger("cleanup")


async def cleanup_task():
    """
    Task for cleaning up temporary files and completed downloads.
    """
    while True:
        try:
            if os.path.exists(settings.TEMP_DIR):
                now = datetime.now()
                for filename in os.listdir(settings.TEMP_DIR):
                    filepath = os.path.join(settings.TEMP_DIR, filename)
                    try:
                        file_mod_time = datetime.fromtimestamp(
                            os.path.getmtime(filepath)
                        )
                        file_age = now - file_mod_time

                        is_active_download = False
                        for download_id, info in download_tasks.items():
                            if (
                                info.filename
                                and os.path.basename(info.filename) in filename
                            ):
                                is_active_download = True
                                break

                        if not is_active_download and file_age > timedelta(minutes=60):
                            logger.info(f"Removing abandoned file: {filepath}")
                            os.remove(filepath)

                        for download_id, info in list(download_tasks.items()):
                            if (
                                info.status == "completed"
                                and info.completed_at
                                and now - info.completed_at > timedelta(minutes=30)
                            ):

                                download_tasks.pop(download_id, None)
                                logger.info(f"Removed download entry: {download_id}")
                    except Exception as e:
                        logger.error(f"Error cleaning up file {filepath}: {str(e)}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
        await asyncio.sleep(300)
