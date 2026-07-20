"""Auth router: token issuance and user management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator

from app import auth, db

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("admin", "analyst", "viewer"):
            raise ValueError("role must be admin, analyst, or viewer")
        return v


class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    is_active: bool


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/token", response_model=TokenResponse, summary="Obtain a JWT access token")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = db.find_one(db.users, username=form.username)
    if not user or not auth.verify_password(form.password, user["hashed_pwd"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    token = auth.create_access_token({"sub": str(user["user_id"])})
    return TokenResponse(access_token=token)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             summary="Register a new user (admin only)")
def create_user(
    body: UserCreate,
    current_user: Annotated[dict, Depends(auth.require_admin)],
):
    if db.find_one(db.users, username=body.username):
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.find_one(db.users, email=body.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    uid = db.seq_users.nextval()
    row = {
        "user_id": uid,
        "username": body.username,
        "email": body.email,
        "hashed_pwd": auth.hash_password(body.password),
        "role": body.role,
        "is_active": True,
        "created_at": db.utcnow(),
    }
    db.users[uid] = row
    return UserResponse(**{k: row[k] for k in UserResponse.model_fields})


@router.get("/users/me", response_model=UserResponse, summary="Get current user profile")
def get_me(current_user: Annotated[dict, Depends(auth.get_current_user)]):
    return UserResponse(**{k: current_user[k] for k in UserResponse.model_fields})


@router.get("/users", response_model=list[UserResponse], summary="List all users (admin only)")
def list_users(current_user: Annotated[dict, Depends(auth.require_admin)]):
    return [UserResponse(**{k: u[k] for k in UserResponse.model_fields}) for u in db.users.values()]


@router.patch("/users/{user_id}/deactivate", response_model=UserResponse,
              summary="Deactivate a user (admin only)")
def deactivate_user(
    user_id: int,
    current_user: Annotated[dict, Depends(auth.require_admin)],
):
    user = db.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user["user_id"] == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    user["is_active"] = False
    return UserResponse(**{k: user[k] for k in UserResponse.model_fields})


@router.post("/users/me/change-password", status_code=204,
             summary="Change own password")
def change_password(
    body: PasswordChange,
    current_user: Annotated[dict, Depends(auth.get_current_user)],
):
    if not auth.verify_password(body.current_password, current_user["hashed_pwd"]):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    current_user["hashed_pwd"] = auth.hash_password(body.new_password)
