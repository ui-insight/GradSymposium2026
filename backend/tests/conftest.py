"""Keep test collection independent of local deployment credentials/drivers."""

import os

os.environ["GPSA_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["GPSA_SEED_HISTORICAL_EVENT"] = "false"
