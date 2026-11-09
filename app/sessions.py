import secrets

from fastapi import Response

from config import SESSION_COOKIE


def guest_session(response: Response, session_id: str | None) -> str:
    if session_id and len(session_id) == 64 and all(char in "0123456789abcdef" for char in session_id):
        return session_id

    session_id = secrets.token_hex(32)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return session_id