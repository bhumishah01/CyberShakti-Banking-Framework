from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.server.api.deps import current_user
from src.server.db.session import get_db
from src.server.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from src.server.services.auth import login_user, register_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user = register_user(
            db,
            user_id=payload.user_id.strip(),
            phone=payload.phone,
            password=payload.password,
            role=payload.role,
        )
        return {"status": "created", "user_id": user.user_id, "role": user.role}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        token, role = login_user(
            db,
            user_id=payload.user_id.strip(),
            password=payload.password,
            device_id=payload.device_id,
        )
        return TokenResponse(access_token=token, role=role)
    except PermissionError:
        raise HTTPException(status_code=401, detail="invalid_credentials")


@router.get("/me")
def me(user=Depends(current_user)) -> dict:
    return {"user_id": user.user_id, "role": user.role}
