from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import time
from typing import Dict

from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
rate_limit_dict: Dict[str, Dict[str, float]] = {}


async def get_api_key(api_key: str = Depends(api_key_header)):
    if not settings.REQUIRE_API_KEY:
        return True
    if api_key == settings.API_KEY:
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key"
    )


async def check_rate_limit(client_ip: str = Depends(lambda: "127.0.0.1")):
    if not settings.ENABLE_RATE_LIMITING:
        return True

    now = time.time()

    for ip in list(rate_limit_dict.keys()):
        if now - rate_limit_dict[ip]["timestamp"] > 60:
            del rate_limit_dict[ip]

    if client_ip not in rate_limit_dict:
        rate_limit_dict[client_ip] = {"count": 1, "timestamp": now}
    else:
        if now - rate_limit_dict[client_ip]["timestamp"] > 60:
            rate_limit_dict[client_ip] = {"count": 1, "timestamp": now}
        else:
            rate_limit_dict[client_ip]["count"] += 1

            if rate_limit_dict[client_ip]["count"] > settings.RATE_LIMIT_REQUESTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Try again later.",
                )

    return True
