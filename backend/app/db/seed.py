"""Seed data for development database."""

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.models.event import Event
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.project import Project
from app.models.rubric import Rubric
from app.models.rubric_criterion import RubricCriterion
from app.models.score import Score
from app.models.user import User

EVENT_ID = "evt-2026-symposium"


async def seed_database(db: AsyncSession) -> None:
    """Populate database with dev data. Idempotent — skips if data exists."""
    existing = await db.execute(select(Event).limit(1))
    if existing.scalar():
        return

    # --- Admin user ---
    admin = User(
        User_ID=str(uuid.uuid4()),
        Username="admin",
        Hashed_Password=hash_password("admin"),
        Role="admin",
    )
    db.add(admin)

    # --- Event ---
    event = Event(
        Event_ID=EVENT_ID,
        Event_Name="2026 Graduate Student Symposium",
        Event_Date=datetime.date(2026, 3, 13),
        Location="Bruce Pitman Center — International Ballroom",
        Description="Annual GPSA Graduate Student Symposium at the University of Idaho",
        Is_Active=True,
    )
    db.add(event)

    # --- Rubrics ---
    art_rubric_id = "rubric-art"
    poster_rubric_id = "rubric-poster"

    art_rubric = Rubric(
        Rubric_ID=art_rubric_id,
        Event_ID=EVENT_ID,
        Rubric_Name="Art Rubric",
        Category="Art",
        Max_Score=9,
        Description="Scoring rubric for art presentations",
    )
    poster_rubric = Rubric(
        Rubric_ID=poster_rubric_id,
        Event_ID=EVENT_ID,
        Rubric_Name="Poster Rubric",
        Category="Poster",
        Max_Score=36,
        Description="Scoring rubric for poster presentations",
    )
    db.add_all([art_rubric, poster_rubric])

    # --- Art Criteria ---
    art_criteria = [
        ("Craftsmanship/Technical Skill", None, 1),
        ("Creativity and Originality", None, 2),
        ("Communication of Ideas and Theme", None, 3),
    ]
    for name, group, order in art_criteria:
        db.add(
            RubricCriterion(
                Rubric_ID=art_rubric_id,
                Criterion_Name=name,
                Criterion_Group=group,
                Sort_Order=order,
            )
        )

    # --- Poster Criteria ---
    poster_criteria = [
        ("Poster Layout", "Poster Content", 1),
        ("Relevant and brief introduction", "Poster Content", 2),
        ("Explicit mention of research question & rationale", "Poster Content", 3),
        (
            "Appropriate description of research methodology and data analysis",
            "Poster Content",
            4,
        ),
        ("Discussion of results accurately interprets results", "Poster Content", 5),
        ("Appropriate use & explanation of graphics", "Poster Content", 6),
        (
            "Presentation was comprehensive & had a cohesive flow",
            "Communication Skills",
            7,
        ),
        (
            "Research's impact on field or community clearly stated",
            "Communication Skills",
            8,
        ),
        (
            "Student presented information in an engaging, enthusiastic manner",
            "Communication Skills",
            9,
        ),
        ("Appropriate use of technical language", "Professional Presentation", 10),
        (
            "Adequate handling of questions and feedback",
            "Professional Presentation",
            11,
        ),
        (
            "Poster is legible and has appropriate formatting and style",
            "Professional Presentation",
            12,
        ),
    ]
    for name, group, order in poster_criteria:
        db.add(
            RubricCriterion(
                Rubric_ID=poster_rubric_id,
                Criterion_Name=name,
                Criterion_Group=group,
                Sort_Order=order,
            )
        )

    # --- Sample Projects ---
    poster_projects = [
        ("P-01", "Impact of Climate Change on Idaho Salmon Populations", "Jane", "Smith", "Biology", "COSDA", "Dr. Rivera"),
        ("P-02", "Machine Learning for Crop Disease Detection", "Michael", "Chen", "Computer Science", "CoE", "Dr. Patel"),
        ("P-03", "Novel Catalysts for Green Hydrogen Production", "Sarah", "Johnson", "Chemistry", "COSDA", "Dr. Kim"),
        ("P-04", "Anxiety Interventions in Rural College Students", "David", "Williams", "Psychology", "COSDA", "Dr. Thompson"),
        ("P-05", "Seismic Resilience of Idaho Bridge Infrastructure", "Maria", "Garcia", "Civil Engineering", "CoE", "Dr. Anderson"),
        ("P-06", "Wildfire Risk Modeling in the Inland Northwest", "James", "Brown", "Natural Resources", "CNR", "Dr. Harrison"),
        ("P-07", "CRISPR Applications in Lentil Crop Improvement", "Emily", "Davis", "Plant Sciences", "CALS", "Dr. Wilson"),
        ("P-08", "Water Quality Assessment of the Palouse Basin", "Robert", "Martinez", "Environmental Science", "COSDA", "Dr. Lee"),
        ("P-09", "Nez Perce Language Revitalization Through Technology", "Lisa", "Taylor", "Education", "CoEd", "Dr. Whitman"),
        ("P-10", "Economic Impact of Remote Work on Rural Communities", "Kevin", "Anderson", "Economics", "CBE", "Dr. Foster"),
    ]

    project_ids = []
    for num, title, first, last, dept, college, advisor in poster_projects:
        pid = str(uuid.uuid4())
        project_ids.append(pid)
        db.add(
            Project(
                Project_ID=pid,
                Event_ID=EVENT_ID,
                Project_Number=num,
                Project_Title=title,
                Presenter_First_Name=first,
                Presenter_Last_Name=last,
                Department=dept,
                College=college,
                Advisor_Name=advisor,
                Category="Poster",
                Table_Number=f"T-{num[2:]}",
            )
        )

    art_projects = [
        ("A-01", "Reflections on Rural Identity", "Alex", "Rivera", "Art & Architecture", "CAA", "Prof. Morgan"),
        ("A-02", "Palouse Landscapes in Mixed Media", "Jordan", "Lee", "Art & Architecture", "CAA", "Prof. Chen"),
        ("A-03", "Digital Narratives of Migration", "Sam", "Patel", "Art & Architecture", "CAA", "Prof. Rivera"),
        ("A-04", "Sound and Space: An Interactive Installation", "Taylor", "Kim", "Music", "CLASS", "Prof. Adams"),
        ("A-05", "Ceramic Forms Inspired by Idaho Geology", "Morgan", "White", "Art & Architecture", "CAA", "Prof. Stone"),
    ]

    art_project_ids = []
    for num, title, first, last, dept, college, advisor in art_projects:
        pid = str(uuid.uuid4())
        art_project_ids.append(pid)
        db.add(
            Project(
                Project_ID=pid,
                Event_ID=EVENT_ID,
                Project_Number=num,
                Project_Title=title,
                Presenter_First_Name=first,
                Presenter_Last_Name=last,
                Department=dept,
                College=college,
                Advisor_Name=advisor,
                Category="Art",
                Table_Number=f"T-A{num[2:]}",
            )
        )

    # --- Sample Judges ---
    judges_data = [
        ("Dr. Patricia", "Hernandez", "Biology", "HRN47K"),
        ("Dr. Thomas", "Wright", "Computer Science", "WRT82M"),
        ("Dr. Nancy", "Park", "Chemistry", "PRK35N"),
        ("Prof. Richard", "Cole", "Art & Architecture", "CLE69R"),
        ("Dr. Sandra", "Murphy", "Psychology", "MRP24S"),
    ]

    judge_ids = []
    for first, last, dept, code in judges_data:
        jid = str(uuid.uuid4())
        judge_ids.append(jid)
        db.add(
            Judge(
                Judge_ID=jid,
                Event_ID=EVENT_ID,
                First_Name=first,
                Last_Name=last,
                Department=dept,
                Access_Code=code,
            )
        )

    await db.flush()

    # --- Sample Scores (judges 0-2 scoring poster projects 0-3) ---
    # Get poster rubric criteria IDs
    crit_result = await db.execute(
        select(RubricCriterion)
        .where(RubricCriterion.Rubric_ID == poster_rubric_id)
        .order_by(RubricCriterion.Sort_Order)
    )
    poster_crits = crit_result.scalars().all()

    art_crit_result = await db.execute(
        select(RubricCriterion)
        .where(RubricCriterion.Rubric_ID == art_rubric_id)
        .order_by(RubricCriterion.Sort_Order)
    )
    art_crits = art_crit_result.scalars().all()

    import random

    random.seed(42)

    # 3 judges score 4 poster projects each
    for j_idx in range(3):
        for p_idx in range(4):
            for crit in poster_crits:
                db.add(
                    Score(
                        Judge_ID=judge_ids[j_idx],
                        Project_ID=project_ids[p_idx],
                        Criterion_ID=crit.Criterion_ID,
                        Score_Value=random.randint(1, 3),
                    )
                )

    # 2 judges score 2 art projects each
    for j_idx in range(3, 5):
        for p_idx in range(2):
            for crit in art_crits:
                db.add(
                    Score(
                        Judge_ID=judge_ids[j_idx],
                        Project_ID=art_project_ids[p_idx],
                        Criterion_ID=crit.Criterion_ID,
                        Score_Value=random.randint(1, 3),
                    )
                )

    # --- Sample Assignments ---
    for j_idx in range(3):
        for p_idx in range(2):
            db.add(
                JudgeAssignment(
                    Judge_ID=judge_ids[j_idx],
                    Project_ID=project_ids[p_idx],
                )
            )

    await db.commit()
