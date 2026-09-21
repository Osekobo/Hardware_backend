import os
from fastapi import Response

from auth.jwt import ACCESS_TOKEN_EXPIRE_MINUTES

ACCESS_TOKEN_COOKIE_NAME = "access_token"
ACCESS_TOKEN_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"


def set_access_token_cookie(response: Response, token: str):
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES) * 60,
        httponly=True,
        secure=ACCESS_TOKEN_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_access_token_cookie(response: Response):
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        path="/",
    )