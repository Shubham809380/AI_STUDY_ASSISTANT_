"""Tests for the SQLite database layer (no external network required)."""

import pytest


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    import database.database as database

    db_path = tmp_path / "test_study_assistant.db"
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.initialize_database()
    return database


class TestDatabase:
    def test_initialization_creates_demo_user(self, temp_db):
        user = temp_db.get_user_by_email("demo@student.com")
        assert user is not None
        assert user["name"] == "Demo Student"

    def test_create_and_get_subjects(self, temp_db):
        user_id = temp_db.get_user_by_email("demo@student.com")["user_id"]
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        subjects = temp_db.get_subjects(user_id)
        names = [row["subject_name"] for row in subjects]
        assert "Mathematics" in names

    def test_save_note_and_count(self, temp_db):
        user_id = temp_db.get_user_by_email("demo@student.com")["user_id"]
        subject_id = temp_db.add_subject(user_id, "Physics")
        note_id = temp_db.save_note(
            user_id=user_id,
            subject_id=subject_id,
            title="Laws of Motion",
            source_text="source",
            generated_notes="## Explanation\n...",
        )
        assert note_id > 0
        assert temp_db.get_total_notes(user_id) >= 1
        notes = temp_db.get_notes(user_id)
        assert any(row["title"] == "Laws of Motion" for row in notes)

    def test_quiz_and_result_flow(self, temp_db):
        user_id = temp_db.get_user_by_email("demo@student.com")["user_id"]
        subject_id = temp_db.add_subject(user_id, "Chemistry")
        quiz_id = temp_db.create_quiz(
            user_id=user_id,
            subject_id=subject_id,
            topic="Atomic Structure",
            difficulty="Medium",
            total_questions=3,
        )
        temp_db.save_quiz_question(
            quiz_id=quiz_id,
            question_text="What is an atom?",
            option_a="a", option_b="b", option_c="c", option_d="d",
            correct_answer="A",
            explanation="",
        )
        result_id = temp_db.save_quiz_result(
            quiz_id=quiz_id, user_id=user_id, score=2, total_questions=3
        )
        assert result_id > 0
        results = temp_db.get_quiz_results(user_id)
        assert any(row["result_id"] == result_id for row in results)
        assert 0 < temp_db.get_average_score(user_id) <= 100

    def test_study_session_flow(self, temp_db):
        user_id = temp_db.get_user_by_email("demo@student.com")["user_id"]
        subject_id = temp_db.add_subject(user_id, "Biology")
        temp_db.add_study_session(
            user_id=user_id,
            subject_id=subject_id,
            topic="Cell Division",
            duration_minutes=45,
        )
        assert temp_db.get_total_study_sessions(user_id) >= 1
        assert temp_db.get_total_study_minutes(user_id) >= 45
        sessions = temp_db.get_study_sessions(user_id)
        assert any(row["topic"] == "Cell Division" for row in sessions)