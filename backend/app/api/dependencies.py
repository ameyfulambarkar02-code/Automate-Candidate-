import secrets

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def require_user(
    request: Request,
    db: Session = Depends(get_db),
    x_csrf_token: str | None = Header(default=None),
) -> User:
    user_id = request.session.get("user_id")
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in with Google to continue.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        expected = request.session.get("csrf_token", "")
        if not x_csrf_token or not secrets.compare_digest(expected, x_csrf_token):
            raise HTTPException(status_code=403, detail="CSRF token is missing or invalid.")
    return user
