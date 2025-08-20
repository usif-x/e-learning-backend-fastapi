# File: app/core/limiter.py

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings

# Create a Limiter instance.
# `get_remote_address` is the key function that uses the client's IP address to track requests.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=[settings.redis_rate_limit],
)


async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom exception handler for rate-limited requests to return a JSON response.
    """
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Too Many Requests: rate limit exceeded ({exc.detail})",
            "message": "You have made too many requests in a short period. Please try again later.",
        },
    )
