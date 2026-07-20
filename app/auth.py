"""
Authentication and role-based access control.

- Passwords hashed with bcrypt directly (passlib 1.7.4 is incompatible with bcrypt >=4.x).
- JWT access tokens signed with HS256 via python-jose.
- Three roles: admin > analyst > viewer.
  admin   – full CRUD, lock/submit periods, manage users
  analyst – create/edit allocations, cannot submit
  viewer  – read-only
"""

from datetime import timedelta
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.config import settings
from app import db

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = db.utcnow() + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Current-user dependency
# ---------------------------------------------------------------------------

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    payload = _decode_token(token)
    user_id: int | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = db.users.get(int(user_id))
    if user is None or not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


# ---------------------------------------------------------------------------
# Role-checking dependencies  (use as FastAPI dependency)
# ---------------------------------------------------------------------------

ROLE_RANK = {"viewer": 0, "analyst": 1, "admin": 2}


def _require_role(minimum_role: str):
    """Return a FastAPI dependency that enforces a minimum role level."""

    def _checker(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
        user_rank = ROLE_RANK.get(current_user["role"], -1)
        required_rank = ROLE_RANK[minimum_role]
        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{minimum_role}' or above required. Your role: '{current_user['role']}'.",
            )
        return current_user

    return _checker


require_viewer  = _require_role("viewer")
require_analyst = _require_role("analyst")
require_admin   = _require_role("admin")
