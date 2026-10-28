"""Present the existing unweighted tally without making a tie-breaking decision."""

from collections import Counter

from app.schemas.attendee_report import AttendeeChoiceEntry, AttendeeChoiceReport


def attendee_choice_report(tally):
    # The canonical tally supplies vote-descending, poster-number-stable order.
    # Shared competition ranks make that secondary order visibly non-decisive.
    counts = Counter(row["Votes"] for row in tally)
    ranks = {}
    entries = []
    for index, row in enumerate(tally, 1):
        rank = ranks.setdefault(row["Votes"], index)
        entries.append(
            AttendeeChoiceEntry(
                Project_Number=row["Project_Number"],
                Presenter_Display_Name=row["Presenter_Display_Name"],
                Project_Title=row["Project_Title"],
                Votes=row["Votes"],
                Vote_Rank=rank,
                Tied_Count=counts[row["Votes"]],
            )
        )
    cutoff = entries[9].Votes if len(entries) >= 10 else None
    additional = [row for row in entries[10:] if row.Votes == cutoff]
    return AttendeeChoiceReport(
        Eligible_Count=len(entries),
        Top_Ten=entries[:10],
        Additional_Cutoff_Ties=additional,
        Cutoff_Votes=cutoff,
        Cutoff_Spans_Ten=bool(additional),
    ).model_dump()
