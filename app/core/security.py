import secrets

import jwt
from fastapi import Request, Response

from app.config import settings
from app.core.exceptions import InvalidTokenError

AUTH_COOKIE_NAME = "frill_session"
CSRF_COOKIE_NAME = "frill_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def verify_supabase_jwt(token: str) -> dict:
    try:
        return jwt.decode(
            token, settings.supabase_jwt_secret, algorithms=["HS256"], audience="authenticated"
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError() from exc


def set_auth_cookie(response: Response, token: str, max_age_seconds: int = 60 * 60 * 24 * 7) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,                       # JS can never read this — kills XSS token theft
        secure=settings.is_production,        # False locally (http), True in prod (https)
        samesite="strict",
        max_age=max_age_seconds,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/")


def set_csrf_cookie(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,   # frontend JS must read this one to echo it back in a header
        secure=settings.is_production,
        samesite="strict",
        path="/",
    )
    return token


def verify_csrf(request: Request) -> None:
    """Double-submit cookie check. Applied globally via middleware (see main.py).
    FIX C4 — was defined but never wired in the original plan."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if not cookie_token or not header_token or cookie_token != header_token:
        raise InvalidTokenError("CSRF check failed")