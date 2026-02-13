import os
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Bypass Rate Limit for Development
BYPASS_RATE_LIMIT = os.getenv("BYPASS_RATE_LIMIT", "false").lower() == "true"

def get_user_id(request: Request):
    """
    Returns the user ID from the request state if authenticated.
    Falls back to remote IP address if not authenticated (though our endpoints are protected).
    """
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user
    
    # Fallback to IP if auth fails or not yet processed (shouldn't happen on protected routes)
    return get_remote_address(request)

# Initialize Limiter
# key_func: determines what to identify the user by (User ID > IP)
# enabled: allows disabling the limiter via env variable
limiter = Limiter(key_func=get_user_id, enabled=not BYPASS_RATE_LIMIT)
