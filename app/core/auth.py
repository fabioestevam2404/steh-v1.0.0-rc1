from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Header, HTTPException, status

from app.core.config import settings


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: tuple[str, ...]


def get_principal(
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    if not settings.auth_enabled:
        return Principal(subject="local-development", roles=("steh_user",))

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=[settings.auth_jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from exc

    roles = tuple(claims.get("roles", []))
    if settings.auth_required_role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role.",
        )

    return Principal(subject=str(claims["sub"]), roles=roles)
