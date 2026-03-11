"""Seed data for the 2026 Graduate Student Symposium."""

import datetime
import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.password import hash_password
from app.models.event import Event
from app.models.judge import Judge
from app.models.project import Project
from app.models.rubric import Rubric
from app.models.rubric_criterion import RubricCriterion
from app.models.user import User

EVENT_ID = "evt-2026-symposium"


async def ensure_admin(db: AsyncSession) -> None:
    """Create default admin user if none exists. Runs in all environments."""
    existing = await db.execute(select(User).where(User.Role == "admin").limit(1))
    if existing.scalar():
        return

    admin = User(
        User_ID=str(uuid.uuid4()),
        Username="admin",
        Hashed_Password=hash_password("admin"),
        Role="admin",
    )
    db.add(admin)
    await db.commit()


def _make_access_code(name: str, index: int) -> str:
    """Generate a deterministic 6-char alphanumeric access code."""
    raw = hashlib.sha256(f"{name}-{index}-2026symposium".encode()).hexdigest()
    code = ""
    for ch in raw.upper():
        if ch.isalpha() and len([c for c in code if c.isalpha()]) < 3:
            code += ch
        elif ch.isdigit() and len([c for c in code if c.isdigit()]) < 3:
            code += ch
        if len(code) == 6:
            break
    return code


async def seed_database(db: AsyncSession) -> None:
    """Populate database with real 2026 symposium data. Idempotent."""
    existing = await db.execute(select(Event).limit(1))
    if existing.scalar():
        return

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

    # =====================================================================
    # Real presenter data from "GPSA Expo - Workbook - 2026 COPY.xlsx"
    # =====================================================================

    # Poster presenters (27 accepted)
    # (first, last, email, program, authors)
    poster_presenters = [
        ("Sameer", "Mankotia", "mank8837@vandals.uidaho.edu", "Computer Science", "Sameer Mankotia, Daniel Conte De Leon, Jennifer Johnson-Leung"),
        ("Nate", "Nadal", "nnadal@uidaho.edu", "Natural Resources - Fish & Wildlife", "Nate Nadal"),
        ("Andrea", "Schmutz", "schm8894@vandals.uidaho.edu", "Education", "Andrea Soleta Schmutz, Juhee Kim"),
        ("Sahithi", "Thota", "thot8631@vandals.uidaho.edu", "Electrical Engineering", "Sahithi Thota"),
        ("Japneet", "Kukal", "kuka9993@vandals.uidaho.edu", "Natural Resources", "Japneet Kukal, Lorena A. Portilla, Brian Via, Lucila M. Carias, Maria Auad, Manish Sakhakarmy, Sushil Adhikari, Armando G. McDonald"),
        ("Ruth", "Azike", "azik3672@vandals.uidaho.edu", "Environmental Science", "Azike Ruth Chinazor, Armando McDonald, Ezra Bar-Ziv"),
        ("Sodiq", "Yusuf", "yusu5902@vandals.uidaho.edu", "Natural Resources", "Sodiq Yusuf, Michael Maughan, Armando McDonald"),
        ("Marilyn", "Stein", "stei0434@vandals.uidaho.edu", "Nutritional Sciences", "Marilyn Stein, Yimin Chen, Ann Frost"),
        ("Edison", "Reyes Proano", "reye0766@vandals.uidaho.edu", "Plant Science", "Edison Reyes-Proano, Gardenia E. Orellana, Jeffrey Chojnacky, Apekshya Senchuri, Erik J. Wenninger, Alexander V. Karasev"),
        ("Emmanuella", "Afolabi", "afol9291@vandals.uidaho.edu", "Anthropology", "Emmanuella Afolabi"),
        ("Keeya", "Beausoleil", "beau4371@vandals.uidaho.edu", "Geology", "Keeya Beausoleil, Timothy Bartholomaus, Alison Criscitiello, Eric Mittelstaedt, Elowyn Yager"),
        ("Ashton", "Sellke", "sell9149@vandals.uidaho.edu", "Plant Science", "Ashton Sellke, Timothy Prather"),
        ("Yuan", "Yuan", "yuan8150@vandals.uidaho.edu", "Biological Engineering", "Yuan Yuan"),
        ("Shahriar Md Arifur", "Rahman", "rahm8493@vandals.uidaho.edu", "Environmental Science", "Shahriar Md Arifur Rahman, Chris A.B. Zajchowski, Muhammad Moniruzzaman, Joohee Lee, Hana Kim"),
        ("Jacob", "Spickelmire", "spic6711@vandals.uidaho.edu", "English", "Jacob Spickelmire"),
        ("Ariana", "Cerreta", "cerr0733@vandals.uidaho.edu", "Natural Resources", "Ariana L. Cerreta, David E. Ausband"),
        ("Hannah", "Stolfus", "stol5899@vandals.uidaho.edu", "Agricultural Education", "Hannah Stolfus"),
        ("Timothy", "Stevens", "stev1754@vandals.uidaho.edu", "Mechanical Engineering", "Daniel Robertson, Timothy Stevens"),
        ("Evelyn", "Roldan Vernon", "rold1482@vandals.uidaho.edu", "Nutritional Sciences", "Evelyn Roldán Vernon, Wilton Pérez, Ginny Lane"),
        ("Isaac", "Looney", "loon1344@vandals.uidaho.edu", "Mechanical Engineering", "Isaac Looney, Daniel Robertson"),
        ("Hussain", "Qazaq", "qaza0118@vandals.uidaho.edu", "Nutritional Sciences", "Ginny Lane, Hussain Qazaq"),
        ("Leela", "Appili", "appi5393@vandals.uidaho.edu", "Plant Science", "Leela Appili"),
        ("Alireza", "Majidi", "maji2418@vandals.uidaho.edu", "Nutritional Sciences", "Alireza Majidi, Edris Afsharkohan, Mahdi Hejazi, Mojtaba Shafiee"),
        ("Benjamin", "Morenas", "more6244@vandals.uidaho.edu", "Biological Engineering", "Benjamin Morenas, Ekow Agyekum-Oduro, Alia Nasir, Yuan Yuan, Sarah Wu"),
        ("Ahmad", "Mukhtar", "mukh9219@vandals.uidaho.edu", "Chemical Engineering", "Ahmad Mukhtar, Yuan Yuan, Jonathan Stromberg, Ben Morenas, Sarah Wu"),
        ("Ekow", "Agyekum-Oduro", "agye3445@vandals.uidaho.edu", "Chemical Engineering", "Ekow Agyekum-Oduro, Ahmad Mukhtar, Sidra Saqib, Robinson Ndeddy Aka, Sarah Wu"),
        ("Alia", "Nasir", "nasi9466@vandals.uidaho.edu", "Biological Engineering", "Alia Nasir, Benjamin Morenas, Dinithi Mohotti, Ekow Agyekum-Oduro, Sarah Wu"),
    ]

    for i, (first, last, email, dept, authors) in enumerate(poster_presenters, start=1):
        num = f"P-{i:02d}"
        db.add(
            Project(
                Project_ID=str(uuid.uuid4()),
                Event_ID=EVENT_ID,
                Project_Number=num,
                Project_Title=f"{first} {last} — {dept}",
                Presenter_First_Name=first,
                Presenter_Last_Name=last,
                Presenter_Email=email,
                Department=dept,
                College=None,
                Advisor_Name=authors,
                Category="Poster",
                Table_Number=f"T-{i:02d}",
            )
        )

    # Art presenters (3 accepted)
    art_presenters = [
        ("Luna", "Migueles Miralles", "Migu3546@vandals.uidaho.edu", "Art", "Luna Migueles Miralles"),
        ("Paige", "O'Callaghan", "ocal7704@vandals.uidaho.edu", "Theatre Arts", "Paige O'Callaghan"),
        ("Kyle", "Silligman", "sill5899@vandals.uidaho.edu", "Art", "Kyle Silligman"),
    ]

    for i, (first, last, email, dept, authors) in enumerate(art_presenters, start=1):
        num = f"A-{i:02d}"
        db.add(
            Project(
                Project_ID=str(uuid.uuid4()),
                Event_ID=EVENT_ID,
                Project_Number=num,
                Project_Title=f"{first} {last} — {dept}",
                Presenter_First_Name=first,
                Presenter_Last_Name=last,
                Presenter_Email=email,
                Department=dept,
                College=None,
                Advisor_Name=authors,
                Category="Art",
                Table_Number=f"T-A{i:02d}",
            )
        )

    # =====================================================================
    # Real judge data from "GPSA Expo - Workbook - 2026 COPY.xlsx"
    # (Final List column)
    # =====================================================================

    judges_data = [
        ("Barrie", "Robison", "brobison@uidaho.edu", "IIDS, IMCI - COS"),
        ("Beth", "Ropski", "eropski@uidaho.edu", "CETL - EHHS"),
        ("Jennifer", "Wilcox", "jwilcox@uidaho.edu", "Biology"),
        ("Aaron", "Johnson", "acjohnson@uidaho.edu", "Art & Architecture"),
        ("Michael", "Brandt", "brandt@uidaho.edu", "Theatre Arts"),
        ("Ann", "Frost", "afrost@uidaho.edu", "EHHS"),
        ("Margaret", "Pinnell", "mpinnell@uidaho.edu", "CETL"),
        ("Brian", "Tibayan", "btibayan@uidaho.edu", "EHHS"),
        ("Ginny", "Lane", "vlane@uidaho.edu", "Nutritional Sciences"),
        ("Ginger", "Carney", None, "COS"),
        ("Herbert", "Hess", "hhess@uidaho.edu", "Electrical & Computer Engineering"),
        ("Rowdy", "Sanford", None, "Electrical & Computer Engineering"),
        ("Tracey", "Peters", "tpeters@uidaho.edu", "Animal, Veterinary & Food Science"),
        ("Phillip", "Hagen", None, "GPSA"),
        ("Ritchie", "Thaxton", None, "GPSA"),
        ("Rita", "Franco", None, "GPSA"),
        ("KT", "Turner", None, "GPSA"),
        ("Zachary", "Foley", None, "GPSA"),
        ("Rafiatu", "Salia", None, "GPSA"),
    ]

    for i, (first, last, email, dept) in enumerate(judges_data):
        code = _make_access_code(f"{first}{last}", i)
        db.add(
            Judge(
                Judge_ID=str(uuid.uuid4()),
                Event_ID=EVENT_ID,
                First_Name=first,
                Last_Name=last,
                Email=email,
                Department=dept,
                Access_Code=code,
            )
        )

    await db.commit()
