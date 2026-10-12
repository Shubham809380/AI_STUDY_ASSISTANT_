"""Tests for the add-subject feature (validation + parameterized storage)."""

import pytest

from database import database
from services import display_utils


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test_subjects.db"
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.initialize_database()
    return database


def _demo_user(db):
    return db.get_user_by_email("demo@student.com")["user_id"]


class TestSubjectValidation:
    @pytest.mark.parametrize("name", ["", "   ", "\n\t", None])
    def test_empty_or_whitespace_rejected(self, name):
        assert display_utils.validate_subject_name(name) is not None

    def test_over_50_characters_rejected(self):
        assert (
            display_utils.validate_subject_name("x" * 51)
            is not None
        )

    def test_exactly_50_characters_accepted(self):
        assert display_utils.validate_subject_name("x" * 50) is None

    def test_duplicate_rejected_case_insensitive(self):
        existing = ["Mathematics", "Physics"]
        assert (
            display_utils.validate_subject_name("mathematics", existing)
            is not None
        )
        assert (
            display_utils.validate_subject_name("  MATHEMATICS  ", existing)
            is not None
        )

    def test_similar_but_distinct_name_accepted(self):
        existing = ["Mathematics"]
        assert display_utils.validate_subject_name("Math", existing) is None

    def test_valid_name_accepted(self):
        assert (
            display_utils.validate_subject_name("Biology", ["Mathematics"])
            is None
        )

    def test_normalize_trims_whitespace(self):
        assert display_utils.normalize_subject_name("  Biology  ") == "Biology"


class TestAddSubjectStorage:
    def test_valid_add_stores_subject(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Biology")
        assert subject_id > 0

        names = [
            subject["subject_name"]
            for subject in temp_db.get_subjects(user_id)
        ]
        assert "Biology" in names

    def test_normalized_name_stored_trimmed(self, temp_db):
        user_id = _demo_user(temp_db)
        cleaned_name = display_utils.normalize_subject_name("  Chemistry  ")
        temp_db.add_subject(user_id, cleaned_name)

        names = [
            subject["subject_name"]
            for subject in temp_db.get_subjects(user_id)
        ]
        assert "Chemistry" in names
        assert "  Chemistry  " not in names

    def test_sql_injection_stored_as_plain_text(self, temp_db):
        user_id = _demo_user(temp_db)
        malicious = "x'); DROP TABLE subjects;--"
        temp_db.add_subject(user_id, malicious)

        names = [
            subject["subject_name"]
            for subject in temp_db.get_subjects(user_id)
        ]
        assert malicious in names

        temp_db.add_subject(user_id, "Safe Subject")

        assert len(temp_db.get_subjects(user_id)) >= 2