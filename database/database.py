import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


DATABASE_PATH = Path(__file__).parent / "study_assistant.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    connection = get_connection()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
        schema = file.read()

    connection.executescript(schema)

    existing_user = connection.execute(
        """
        SELECT user_id
        FROM users
        WHERE email = ?
        """,
        ("demo@student.com",)
    ).fetchone()

    if existing_user is None:
        connection.execute(
            """
            INSERT INTO users (name, email)
            VALUES (?, ?)
            """,
            ("Demo Student", "demo@student.com")
        )

    connection.commit()
    connection.close()

def create_user(name, email=None):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO users (name, email)
        VALUES (?, ?)
        """,
        (name, email)
    )

    connection.commit()
    user_id = cursor.lastrowid
    connection.close()

    return user_id


def get_user(user_id):
    connection = get_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return user
def get_user_by_email(email):
    connection = get_connection()

    user = connection.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (email,)
    ).fetchone()

    connection.close()

    return user

def add_subject(user_id, subject_name):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO subjects (user_id, subject_name)
        VALUES (?, ?)
        """,
        (user_id, subject_name)
    )

    connection.commit()
    subject_id = cursor.lastrowid
    connection.close()

    return subject_id
def save_note(
    user_id,
    subject_id,
    title,
    source_text,
    generated_notes
):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO notes (
            user_id,
            subject_id,
            title,
            source_text,
            generated_notes
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            subject_id,
            title,
            source_text,
            generated_notes
        )
    )

    connection.commit()

    note_id = cursor.lastrowid

    connection.close()

    return note_id


def get_subjects(user_id):
    connection = get_connection()

    subjects = connection.execute(
        """
        SELECT *
        FROM subjects
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return subjects
def get_notes(user_id):
    connection = get_connection()

    notes = connection.execute(
        """
        SELECT
            notes.note_id,
            notes.title,
            notes.generated_notes,
            notes.created_at,
            subjects.subject_name
        FROM notes
        LEFT JOIN subjects
            ON notes.subject_id = subjects.subject_id
        WHERE notes.user_id = ?
        ORDER BY notes.created_at DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return notes
def create_quiz(
    user_id,
    subject_id,
    topic,
    difficulty,
    total_questions
):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO quizzes (
            user_id,
            subject_id,
            topic,
            difficulty,
            total_questions
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            subject_id,
            topic,
            difficulty,
            total_questions
        )
    )

    connection.commit()

    quiz_id = cursor.lastrowid

    connection.close()

    return quiz_id


def save_quiz_question(
    quiz_id,
    question_text,
    option_a,
    option_b,
    option_c,
    option_d,
    correct_answer,
    explanation
):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO quiz_questions (
            quiz_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            quiz_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            explanation
        )
    )

    connection.commit()

    question_id = cursor.lastrowid

    connection.close()

    return question_id
def save_quiz_result(
    quiz_id,
    user_id,
    score,
    total_questions
):
    connection = get_connection()

    percentage = (
        score / total_questions * 100
        if total_questions > 0
        else 0
    )

    cursor = connection.execute(
        """
        INSERT INTO quiz_results (
            quiz_id,
            user_id,
            score,
            total_questions,
            percentage
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            quiz_id,
            user_id,
            score,
            total_questions,
            percentage
        )
    )

    connection.commit()

    result_id = cursor.lastrowid

    connection.close()

    return result_id
def get_quiz_results(user_id):
    connection = get_connection()

    results = connection.execute(
        """
        SELECT
            quiz_results.result_id,
            quiz_results.quiz_id,
            quiz_results.score,
            quiz_results.total_questions,
            quiz_results.percentage,
            quiz_results.completed_at,
            quizzes.topic,
            quizzes.difficulty
        FROM quiz_results
        JOIN quizzes
            ON quiz_results.quiz_id = quizzes.quiz_id
        WHERE quiz_results.user_id = ?
        ORDER BY quiz_results.completed_at DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return results
def get_total_notes(user_id):
    connection = get_connection()

    result = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM notes
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return result["total"]


def get_total_quizzes(user_id):
    connection = get_connection()

    result = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM quizzes
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return result["total"]


def get_average_score(user_id):
    connection = get_connection()

    result = connection.execute(
        """
        SELECT AVG(percentage) AS average
        FROM quiz_results
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return result["average"] or 0


def get_total_study_sessions(user_id):
    connection = get_connection()

    result = connection.execute(
        """
        SELECT COUNT(*) AS total
        FROM study_sessions
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return result["total"]
def get_total_study_minutes(user_id):
    connection = get_connection()

    result = connection.execute(
        """
        SELECT COALESCE(SUM(duration_minutes), 0) AS total
        FROM study_sessions
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return result["total"]


def add_study_session(
    user_id,
    subject_id,
    topic,
    duration_minutes
):
    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO study_sessions (
            user_id,
            subject_id,
            topic,
            duration_minutes
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            subject_id,
            topic,
            duration_minutes
        )
    )

    connection.commit()

    session_id = cursor.lastrowid

    connection.close()

    return session_id


def get_study_sessions(user_id):
    connection = get_connection()

    sessions = connection.execute(
        """
        SELECT
            study_sessions.session_id,
            study_sessions.topic,
            study_sessions.duration_minutes,
            study_sessions.session_date,
            subjects.subject_name
        FROM study_sessions
        LEFT JOIN subjects
            ON study_sessions.subject_id = subjects.subject_id
        WHERE study_sessions.user_id = ?
        ORDER BY study_sessions.session_date DESC, study_sessions.session_id DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return sessions


def delete_study_session(session_id):
    """Delete one study session by id, returning the number of rows deleted."""
    connection = get_connection()

    cursor = connection.execute(
        """
        DELETE FROM study_sessions
        WHERE session_id = ?
        """,
        (session_id,)
    )

    connection.commit()

    rows_deleted = cursor.rowcount

    connection.close()

    return rows_deleted


def compute_study_streak(dates, today):
    """Return the consecutive-day study streak ending today (or yesterday).

    ``dates`` is an iterable of ``datetime.date`` study days.  The streak
    anchors on ``today`` (falling back to yesterday when today has no
    session) and walks backwards while each previous day is present.
    """
    study_dates = {d for d in dates}

    if not study_dates:
        return 0

    anchor = today if today in study_dates else today - timedelta(days=1)

    if anchor not in study_dates:
        return 0

    streak = 0
    cursor = anchor

    while cursor in study_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def get_study_streak(user_id, today=None):
    """Return the user's consecutive-day study streak as an integer.

    ``today`` may be injected for testing; it defaults to the real date.
    Duplicate sessions on the same day are counted once.  No sessions
    means a streak of 0.
    """
    connection = get_connection()

    rows = connection.execute(
        """
        SELECT DISTINCT date(session_date) AS study_date
        FROM study_sessions
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    study_dates = [
        datetime.strptime(str(row["study_date"]), "%Y-%m-%d").date()
        for row in rows
        if row["study_date"]
    ]

    reference = today or date.today()

    return compute_study_streak(study_dates, reference)

if __name__ == "__main__":
    initialize_database()

    print("Database initialized successfully.")

    existing_user = get_user_by_email("demo@student.com")

    if existing_user:
        user_id = existing_user["user_id"]
        print(f"Demo user already exists with ID: {user_id}")

    else:
        user_id = create_user(
            "Demo Student",
            "demo@student.com"
        )
        print(f"Demo user created with ID: {user_id}")

    

    user = get_user(user_id)


    print(f"User: {user['name']}")

    subjects = get_subjects(user_id)

    print("Subjects:")

    for subject in subjects:
        print(f"- {subject['subject_name']}")

