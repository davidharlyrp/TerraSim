import os
import httpx
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.error import ErrorCode, get_error_info
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the same directory as this file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# PocketBase URL
# Default to localhost if not provided
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://127.0.0.1:8090")

security = HTTPBearer(auto_error=False)

# Bypass Auth for Development
BYPASS_AUTH = os.getenv("BYPASS_AUTH", "false").lower() == "true"

MOCK_USER = {
    "id": "dev_user_bypass",
    "name": "Developer Bypass",
    "email": "dev@local.test",
    "terrasim_running_count": 0
}

async def verify_token(request: Request = None, credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Verifies the JWT token by calling PocketBase API.
    Returns the user data if valid.
    Supports BYPASS_AUTH for local development.
    """
    token = credentials.credentials if credentials else None

    if not token:
        if BYPASS_AUTH:
            print("🚀 BYPASS_AUTH is enabled. Using Mock User.")
            if request:
                request.state.user = MOCK_USER["id"]
            return MOCK_USER
        raise_auth_error(ErrorCode.AUTH_MISSING_TOKEN, 401)

    try:
        # verify token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/users/auth-refresh",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )

            if response.status_code == 200:
                # Token is valid, return the record/user data
                data = response.json()
                record = data.get("record", {})
                
                # Attach user ID to request state for Rate Limiter
                if request:
                    request.state.user = record.get("id")
                    
                return record
            
            elif response.status_code == 401:
                if BYPASS_AUTH:
                    print("⚠️ Token Invalid but BYPASS_AUTH is enabled. Using Mock User.")
                    if request:
                        request.state.user = MOCK_USER["id"]
                    return MOCK_USER
                # Token Invalid or Expired
                raise_auth_error(ErrorCode.AUTH_INVALID_TOKEN, 401)
            else:
                # Other error (PB down, 404, etc.)
                print(f"Auth Check Failed with status {response.status_code}: {response.text}")
                if BYPASS_AUTH:
                    return MOCK_USER
                raise_auth_error(ErrorCode.AUTH_INVALID_TOKEN, 401)

    except httpx.RequestError as e:
        print(f"Auth Connection Error: {str(e)}")
        # Failing safe for security.
        raise HTTPException(status_code=503, detail="Authentication Service Unavailable")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth Unexpected Error: {str(e)}")
        raise_auth_error(ErrorCode.AUTH_INVALID_TOKEN, 401)

def raise_auth_error(code: ErrorCode, status_code: int):
    info = get_error_info(code)
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code.value,
            "title": info["title"],
            "description": info["description"]
        }
    )

def get_current_user(payload: dict = Depends(verify_token)) -> str:
    """
    Dependency to get the current user ID from the verified token.
    """
    return payload.get("id")

async def record_running_history(user_id: str, token: str):
    """
    Creates a new record in the terrasim_running_history collection in PocketBase.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POCKETBASE_URL}/api/collections/terrasim_running_history/records",
                json={"user_id": user_id},
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0
            )
            if response.status_code != 200:
                print(f"Failed to record running history: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error recording running history: {str(e)}")
