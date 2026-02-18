"""Import all models so Alembic / create_all sees them."""

from app.models.event import Event  # noqa: F401
from app.models.judge import Judge  # noqa: F401
from app.models.judge_assignment import JudgeAssignment  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.rubric import Rubric  # noqa: F401
from app.models.rubric_criterion import RubricCriterion  # noqa: F401
from app.models.score import Score  # noqa: F401
from app.models.user import User  # noqa: F401
