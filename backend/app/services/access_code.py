"""Access code generation for judges."""

import secrets

# Exclude ambiguous characters: 0/O, 1/I/L
CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def generate_access_code() -> str:
    return "".join(secrets.choice(CHARSET) for _ in range(CODE_LENGTH))
