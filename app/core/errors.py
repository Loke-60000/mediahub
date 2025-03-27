from fastapi import HTTPException, status
import logging

logger = logging.getLogger("app")


class DownloadError(HTTPException):
    def __init__(self, detail: str = "Download error occurred"):
        logger.error(f"Download error: {detail}")
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class QueueFullError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Download queue is full. Try again later.",
        )


class NotFoundError(HTTPException):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type} {resource_id} not found",
        )


class BadRequestError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
