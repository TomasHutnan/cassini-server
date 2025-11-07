"""FastAPI dependencies for authentication."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database.queries.users import get_user_by_id
from .jwt import get_user_id_from_token

# Security scheme for Bearer token
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """Dependency to get the current authenticated user from JWT token.
    
    Use this in protected endpoints:
        @router.get("/protected")
        async def protected_route(current_user: dict = Depends(get_current_user)):
            return {"user_id": current_user["id"]}
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        User record as dict
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract token
    token = credentials.credentials
    
    # Get user ID from token
    user_id = get_user_id_from_token(token)
    if user_id is None:
        raise credentials_exception
    
    # Fetch user from database
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user


def get_user_id(current_user: Annotated[dict, Depends(get_current_user)]) -> UUID:
    """Convenience dependency to extract just the user ID.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        User's UUID
    """
    return current_user["id"]
