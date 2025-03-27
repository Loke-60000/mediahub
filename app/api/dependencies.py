from fastapi import Depends
from app.core.security import get_api_key, check_rate_limit


def get_current_user(
    _: bool = Depends(check_rate_limit), __: bool = Depends(get_api_key)
):
    """
    Combined dependency for rate limiting and API key validation.
    """
    return True
