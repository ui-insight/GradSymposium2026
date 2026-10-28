"""Derive locations from permanent numbers, independently of list position."""

import re

from app.models.poster_session import PosterSession


def convention(config):
    if config is None:
        return None
    return {
        key: getattr(config, key)
        for key in ("Odd_Session", "Session_I_Time", "Session_II_Time")
    }


def valid_poster_number(number):
    match = re.fullmatch(r"P-([0-9]+)", number)
    return bool(match and int(match[1]) > 0)


def poster_location(project, config):
    result = {
        "Board_Label": None,
        "Poster_Session": None,
        "Poster_Session_Time": None,
    }
    if project.Category != "Poster":
        return result
    match = re.fullmatch(r"P-([0-9]+)", project.Project_Number)
    if not match or int(match[1]) == 0:
        return result
    result["Board_Label"] = project.Project_Number
    if config is None:
        return result
    odd = int(match[1]) % 2 == 1
    session = (
        config.Odd_Session if odd else ("II" if config.Odd_Session == "I" else "I")
    )
    return {
        "Board_Label": project.Project_Number,
        "Poster_Session": f"Session {session}",
        "Poster_Session_Time": getattr(config, f"Session_{session}_Time"),
    }


async def event_convention(db, event_id):
    return await db.get(PosterSession, event_id)
