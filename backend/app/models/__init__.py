"""Import all models so Alembic / create_all sees them."""

from app.models.ballot import Ballot  # noqa: F401
from app.models.ballot_selection import BallotSelection  # noqa: F401
from app.models.competition import CompetitionSettings  # noqa: F401
from app.models.event import Event  # noqa: F401
from app.models.feedback import Feedback  # noqa: F401
from app.models.judge import Judge  # noqa: F401
from app.models.judge_assignment import JudgeAssignment  # noqa: F401
from app.models.judge_conflict import JudgeConflict  # noqa: F401
from app.models.mentor_review import MentorReview  # noqa: F401
from app.models.poster_session import PosterSession  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_number_reservation import ProjectNumberReservation  # noqa: F401
from app.models.roster_review import RosterDecision, RosterSignoff  # noqa: F401
from app.models.rubric import Rubric  # noqa: F401
from app.models.rubric_criterion import RubricCriterion  # noqa: F401
from app.models.score import Score  # noqa: F401
from app.models.score_override import ScoreOverride  # noqa: F401
from app.models.talk import TalkBallot, TalkCandidate  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.voter import Voter  # noqa: F401
from app.models.voting_round import VotingRound  # noqa: F401
