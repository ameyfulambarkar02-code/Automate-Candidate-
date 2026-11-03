from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import get_settings
from app.models import User
from app.utils.security import decrypt_token

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/forms.body.readonly",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def _client_config() -> dict:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise RuntimeError("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to use Google OAuth.")
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }


def build_flow(state: str | None = None) -> Flow:
    flow = Flow.from_client_config(_client_config(), scopes=SCOPES, state=state)
    flow.redirect_uri = get_settings().google_redirect_uri
    return flow


def user_credentials(user: User) -> Credentials:
    if not user.encrypted_refresh_token:
        raise RuntimeError("Reconnect your Google account to continue.")
    credentials = Credentials(
        token=None,
        refresh_token=decrypt_token(user.encrypted_refresh_token),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=get_settings().google_client_id,
        client_secret=get_settings().google_client_secret,
        scopes=SCOPES,
    )
    credentials.refresh(Request())
    return credentials
