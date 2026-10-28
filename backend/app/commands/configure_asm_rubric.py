"""Install Paul's four-criterion 0–5 ASM draft without opening judging."""

import asyncio

from app.commands.setup_asm import setup
from app.db.engine import async_session_factory, engine
from app.models.competition import CompetitionSettings
from app.services.asm_rubric import configure_asm_rubric


async def configure():
    event_id = await setup()
    async with async_session_factory() as db:
        if not await db.get(CompetitionSettings, event_id):
            db.add(CompetitionSettings(Event_ID=event_id))
        rubric = await configure_asm_rubric(db, event_id)
        await db.commit()
        print(f"ASM rubric ready: {rubric.Rubric_ID}, maximum 20. Judging unchanged.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(configure())
