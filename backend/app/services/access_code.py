"""Access code generation for judges."""

import secrets

from sqlalchemy import select

from app.models.judge import Judge

# Exclude ambiguous characters: 0/O, 1/I/L
CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def generate_access_code() -> str:
    return "".join(secrets.choice(CHARSET) for _ in range(CODE_LENGTH))


async def unique_access_code(db):
    for _ in range(100):
        code = generate_access_code()
        if not await db.scalar(select(Judge.Judge_ID).where(Judge.Access_Code == code)):
            return code
    raise RuntimeError("Unable to generate unique access code")
