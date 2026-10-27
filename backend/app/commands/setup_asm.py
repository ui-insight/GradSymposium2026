"""Create an empty, unpublished ASM event without loading an unconfirmed roster."""

import argparse
import asyncio
import datetime

from sqlalchemy import select, update

import app.models  # noqa: F401
from app.config import settings
from app.db.base import Base
from app.db.engine import async_session_factory, engine
from app.db.schema import ensure_runtime_schema
from app.db.seed import ensure_admin
from app.models.event import Event

EVENT_NAME = "2026 ASM Northwest Branch Meeting"
EVENT_DATE = datetime.date(2026, 10, 31)


async def setup(activate: bool = False) -> str:
    if settings.seed_historical_event:
        raise RuntimeError(
            "Set GPSA_SEED_HISTORICAL_EVENT=false for the ASM deployment"
        )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await ensure_runtime_schema(connection)
    async with async_session_factory() as db:
        await ensure_admin(db)
        event = await db.scalar(
            select(Event).where(
                Event.Event_Name == EVENT_NAME, Event.Event_Date == EVENT_DATE
            )
        )
        if event is None:
            event = Event(
                Event_Name=EVENT_NAME,
                Event_Date=EVENT_DATE,
                Event_End_Date=datetime.date(2026, 11, 1),
                Location="Bruce M. Pitman Center, Vandal Ballroom",
                Description="ASM Northwest Branch Meeting poster presentations",
                Is_Active=False,
                Public_Poster_Lookup_Enabled=False,
            )
            db.add(event)
            await db.flush()
        if activate:
            await db.execute(update(Event).values(Is_Active=False))
            event.Is_Active = True
        await db.commit()
        return event.Event_ID


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--activate",
        action="store_true",
        help="Activate ASM and deactivate other events in this database",
    )
    args = parser.parse_args()
    event_id = asyncio.run(setup(args.activate))
    print(f"ASM event ready: {event_id}. No roster imported or published.")


if __name__ == "__main__":
    main()
