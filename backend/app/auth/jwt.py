"""JWT token creation and decoding."""

import datetime

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = "HS256"


def create_access_token(
    subject: str,
    role: str,
    expires_delta: datetime.timedelta | None = None,
    extra_claims: dict | None = None,
) -> str:
    expire = datetime.datetime.now(datetime.timezone.utc) + (
        expires_delta
        or datetime.timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    if extra_claims:
        payload.update(
            {key: value for key, value in extra_claims.items() if key not in payload}
        )
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
