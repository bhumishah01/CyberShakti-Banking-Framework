from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.server.core.security import decode_token
from src.server.db.session import get_db
from src.server.models.user import User


bearer = HTTPBearer(auto_error=False)


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="missing_token")
    payload = decode_token(creds.credentials)
    user_id = str(payload.get("sub", ""))
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="user_not_found")
    return user


def require_roles(*roles: str):
    def _dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="forbidden")
        return user

    return _dep

