import logging
import secrets

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google.auth.exceptions import GoogleAuthError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_user
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.services.oauth_service import build_flow
from app.utils.security import encrypt_token, new_csrf_token

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@router.post("/google/login")
def google_login(request: Request):
    try:
        flow = build_flow()
        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        request.session.clear()
        request.session["oauth_state"] = state
        return {"authorization_url": authorization_url}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/google/callback")
def google_callback(request: Request, db: Session = Depends(get_db)):
    state = request.query_params.get("state", "")
    expected_state = request.session.pop("oauth_state", "")
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state. Please sign in again.")
    if request.query_params.get("error"):
        raise HTTPException(status_code=400, detail="Google authorization was denied.")
    try:
        flow = build_flow(state=expected_state)
        flow.fetch_token(authorization_response=str(request.url))
        credentials = flow.credentials
        if not credentials.token:
            raise HTTPException(status_code=502, detail="Google did not return an access token.")
        profile = build("oauth2", "v2", credentials=credentials, cache_discovery=False).userinfo().get().execute()
        google_id = profile.get("id")
        if not google_id or not profile.get("email"):
            raise HTTPException(status_code=502, detail="Google did not return the required account profile.")
        user = db.scalar(select(User).where(User.google_id == google_id))
        if not credentials.refresh_token and (user is None or not user.encrypted_refresh_token):
            raise HTTPException(
                status_code=400,
                detail="Google did not provide offline access. Revoke this app in Google Account permissions and try again.",
            )
        if user is None:
            user = User(
                google_id=google_id,
                email=profile["email"],
                name=profile.get("name", ""),
                profile_image=profile.get("picture"),
                encrypted_refresh_token=encrypt_token(credentials.refresh_token),
            )
            db.add(user)
        else:
            user.email = profile["email"]
            user.name = profile.get("name", "")
            user.profile_image = profile.get("picture")
            if credentials.refresh_token:
                user.encrypted_refresh_token = encrypt_token(credentials.refresh_token)
        db.commit()
        request.session.clear()
        request.session["user_id"] = user.id
        request.session["csrf_token"] = new_csrf_token()
        return RedirectResponse(url=get_settings().frontend_url, status_code=303)
    except HTTPException:
        raise
    except (GoogleAuthError, HttpError, requests.RequestException, ValueError, RuntimeError) as exc:
        logger.exception("Google OAuth callback failed")
        raise HTTPException(status_code=502, detail="Google sign-in failed. Check OAuth configuration and try again.") from exc


@router.get("/me")
def auth_me(request: Request, user: User = Depends(require_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "profile_image": user.profile_image,
        "google_connected": bool(user.encrypted_refresh_token),
        "csrf_token": request.session.get("csrf_token"),
    }


@router.post("/logout", dependencies=[Depends(require_user)])
def logout(request: Request):
    request.session.clear()
    return {"status": "signed_out"}


@router.post("/disconnect-google")
def disconnect_google(db: Session = Depends(get_db), user: User = Depends(require_user)):
    if user.encrypted_refresh_token:
        try:
            token = user.encrypted_refresh_token
            from app.utils.security import decrypt_token

            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": decrypt_token(token)},
                timeout=10,
            ).raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Google token revocation failed during disconnect: %s", exc)
    user.encrypted_refresh_token = None
    for form in user.forms:
        form.automatic_processing_enabled = False
    db.commit()
    return {"status": "google_disconnected"}
