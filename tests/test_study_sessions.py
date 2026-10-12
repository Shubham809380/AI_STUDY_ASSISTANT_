"""Tests for study-session polish: validation, streak, history, deletion."""

from datetime import date, datetime, timedelta

import pytest

from database import database
from services import display_utils


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test_study_sessions.db"
    monkeypatch.setattr(database, "DATABASE_PATH", db_path)
    database.initialize_database()
    return database


def _insert_session(db, user_id, subject_id, topic, minutes, when):
    conn = db.get_connection()
    conn.execute(
        """
        INSERT INTO study_sessions (
            user_id, subject_id, topic, duration_minutes, session_date
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, subject_id, topic, minutes, when),
    )
    conn.commit()
    conn.close()


def _demo_user(db):
    return db.get_user_by_email("demo@student.com")["user_id"]


class TestStudySessionStorage:
    def test_save_valid_session_stores_fields(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Biology")
        session_id = temp_db.add_study_session(
            user_id=user_id,
            subject_id=subject_id,
            topic="Cell Division",
            duration_minutes=45,
        )
        assert session_id > 0

        session = temp_db.get_study_sessions(user_id)[0]
        assert session["subject_name"] == "Biology"
        assert session["topic"] == "Cell Division"
        assert session["duration_minutes"] == 45


class TestSessionValidation:
    @pytest.mark.parametrize("topic", ["", "   ", "\n\t", None])
    def test_empty_or_whitespace_topic_rejected(self, topic):
        assert display_utils.validate_study_session_input(topic, 30) is not None

    @pytest.mark.parametrize("duration", [0, -1, -600, None])
    def test_zero_negative_or_missing_duration_rejected(self, duration):
        assert (
            display_utils.validate_study_session_input("Python", duration)
            is not None
        )

    def test_above_max_duration_rejected(self):
        assert (
            display_utils.validate_study_session_input("Python", 601)
            is not None
        )

    def test_valid_input_accepted(self):
        assert display_utils.validate_study_session_input("Python", 30) is None
        assert display_utils.validate_study_session_input("Python", 600) is None

    def test_topic_trimmed(self):
        assert (
            display_utils.normalize_study_topic("  Python Functions  ")
            == "Python Functions"
        )

    def test_topic_truncated_to_max_length(self):
        cleaned = display_utils.normalize_study_topic("x" * 150)
        assert len(cleaned) == 100
        assert cleaned == "x" * 100

    def test_whitespace_topic_normalizes_to_empty(self):
        assert display_utils.normalize_study_topic("   ") == ""


class TestStreak:
    def test_no_sessions_is_zero(self):
        today = date(2026, 10, 12)
        assert database.compute_study_streak([], today) == 0

    def test_today_only(self):
        today = date(2026, 10, 12)
        assert database.compute_study_streak([today], today) == 1

    def test_today_and_yesterday(self):
        today = date(2026, 10, 12)
        dates = [today, today - timedelta(days=1)]
        assert database.compute_study_streak(dates, today) == 2

    def test_three_consecutive_days(self):
        today = date(2026, 10, 12)
        dates = [today, today - timedelta(days=1), today - timedelta(days=2)]
        assert database.compute_study_streak(dates, today) == 3

    def test_gap_breaks_streak(self):
        today = date(2026, 10, 12)
        dates = [
            today,
            today - timedelta(days=1),
            today - timedelta(days=3),
            today - timedelta(days=4),
        ]
        assert database.compute_study_streak(dates, today) == 2

    def test_yesterday_only_counts_one(self):
        today = date(2026, 10, 12)
        assert (
            database.compute_study_streak(
                [today - timedelta(days=1)], today
            )
            == 1
        )

    def test_duplicate_dates_count_once(self):
        today = date(2026, 10, 12)
        assert database.compute_study_streak([today, today], today) == 1

    def test_only_older_day_when_today_and_yesterday_empty_is_zero(self):
        today = date(2026, 10, 12)
        assert (
            database.compute_study_streak(
                [today - timedelta(days=2)], today
            )
            == 0
        )

    def test_db_streak_no_sessions_is_zero(self, temp_db):
        user_id = _demo_user(temp_db)
        assert temp_db.get_study_streak(user_id, today=date(2026, 10, 12)) == 0

    def test_db_streak_today_only(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        _insert_session(
            temp_db, user_id, subject_id, "Algebra", 30, "2026-10-12 09:00:00"
        )
        assert temp_db.get_study_streak(user_id, today=date(2026, 10, 12)) == 1

    def test_db_streak_today_and_yesterday_with_duplicates(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        _insert_session(
            temp_db, user_id, subject_id, "Algebra", 30, "2026-10-12 09:00:00"
        )
        _insert_session(
            temp_db, user_id, subject_id, "Algebra", 45, "2026-10-12 18:00:00"
        )
        _insert_session(
            temp_db, user_id, subject_id, "Calculus", 30, "2026-10-11 09:00:00"
        )
        assert temp_db.get_study_streak(user_id, today=date(2026, 10, 12)) == 2


class TestTimestampFormatter:
    def test_formats_expected_string(self):
        assert (
            display_utils.format_timestamp("2026-08-15 13:02:00")
            == "15 Aug 2026, 1:02 PM"
        )

    def test_formats_midnight(self):
        assert (
            display_utils.format_timestamp("2026-08-15 00:05:00")
            == "15 Aug 2026, 12:05 AM"
        )

    def test_formats_date_only_value(self):
        assert (
            display_utils.format_timestamp("2026-08-15")
            == "15 Aug 2026, 12:00 AM"
        )

    def test_accepts_datetime_object(self):
        value = datetime(2026, 8, 15, 13, 2)
        assert (
            display_utils.format_timestamp(value)
            == "15 Aug 2026, 1:02 PM"
        )

    def test_accepts_date_object(self):
        value = date(2026, 8, 15)
        assert (
            display_utils.format_timestamp(value)
            == "15 Aug 2026, 12:00 AM"
        )

    def test_invalid_value_falls_back_to_raw(self):
        assert display_utils.format_timestamp("not a date") == "not a date"

    def test_none_returns_none(self):
        assert display_utils.format_timestamp(None) is None


class TestTopicCapitalization:
    def test_capitalizes_first_letter(self):
        assert display_utils.capitalize_topic("cell division") == "Cell division"

    def test_already_capitalized_unchanged(self):
        assert display_utils.capitalize_topic("Python") == "Python"

    def test_empty_string(self):
        assert display_utils.capitalize_topic("") == ""


class TestSubjectFilter:
    def test_filter_returns_only_matching_sessions(self, temp_db):
        user_id = _demo_user(temp_db)
        math_id = temp_db.add_subject(user_id, "Mathematics")
        phys_id = temp_db.add_subject(user_id, "Physics")
        _insert_session(
            temp_db, user_id, math_id, "Algebra", 30, "2026-10-10 09:00:00"
        )
        _insert_session(
            temp_db, user_id, math_id, "Geometry", 45, "2026-10-11 09:00:00"
        )
        _insert_session(
            temp_db, user_id, phys_id, "Kinematics", 20, "2026-10-12 09:00:00"
        )

        sessions = temp_db.get_study_sessions(user_id)
        math_sessions = display_utils.filter_study_sessions(
            sessions, "Mathematics"
        )

        assert len(math_sessions) == 2
        assert sum(s["duration_minutes"] for s in math_sessions) == 75
        assert all(
            s["subject_name"] == "Mathematics" for s in math_sessions
        )

    def test_all_returns_everything(self, temp_db):
        user_id = _demo_user(temp_db)
        math_id = temp_db.add_subject(user_id, "Mathematics")
        phys_id = temp_db.add_subject(user_id, "Physics")
        _insert_session(
            temp_db, user_id, math_id, "Algebra", 30, "2026-10-10 09:00:00"
        )
        _insert_session(
            temp_db, user_id, phys_id, "Kinematics", 20, "2026-10-12 09:00:00"
        )

        sessions = temp_db.get_study_sessions(user_id)
        all_sessions = display_utils.filter_study_sessions(sessions, "All")

        assert len(all_sessions) == 2
        assert sum(s["duration_minutes"] for s in all_sessions) == 50

    def test_subject_labels_include_no_subject(self, temp_db):
        user_id = _demo_user(temp_db)
        math_id = temp_db.add_subject(user_id, "Mathematics")
        _insert_session(
            temp_db, user_id, math_id, "Algebra", 30, "2026-10-10 09:00:00"
        )
        _insert_session(
            temp_db, user_id, None, "Reading", 15, "2026-10-11 09:00:00"
        )

        sessions = temp_db.get_study_sessions(user_id)
        labels = display_utils.study_session_subjects(sessions)
        assert labels == ["Mathematics", "No Subject"]


class TestDeleteSession:
    def test_delete_removes_only_chosen_id(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        id1 = temp_db.add_study_session(
            user_id=user_id,
            subject_id=subject_id,
            topic="Algebra",
            duration_minutes=30,
        )
        id2 = temp_db.add_study_session(
            user_id=user_id,
            subject_id=subject_id,
            topic="Geometry",
            duration_minutes=45,
        )

        temp_db.delete_study_session(id1)

        remaining = temp_db.get_study_sessions(user_id)
        assert [s["session_id"] for s in remaining] == [id2]

    def test_delete_missing_id_does_not_crash(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        temp_db.add_study_session(
            user_id=user_id,
            subject_id=subject_id,
            topic="Algebra",
            duration_minutes=30,
        )

        rows = temp_db.delete_study_session(9999)
        assert rows == 0
        assert temp_db.get_total_study_sessions(user_id) == 1


class TestOrdering:
    def test_sessions_returned_newest_first(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        _insert_session(
            temp_db, user_id, subject_id, "Oldest", 30, "2026-10-10 09:00:00"
        )
        _insert_session(
            temp_db, user_id, subject_id, "Middle", 30, "2026-10-11 09:00:00"
        )
        _insert_session(
            temp_db, user_id, subject_id, "Newest", 30, "2026-10-12 09:00:00"
        )

        sessions = temp_db.get_study_sessions(user_id)
        assert [s["topic"] for s in sessions] == ["Newest", "Middle", "Oldest"]

    def test_same_timestamp_tiebreak_by_id_desc(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        _insert_session(
            temp_db, user_id, subject_id, "Older id", 30, "2026-10-12 09:00:00"
        )
        _insert_session(
            temp_db, user_id, subject_id, "Newer id", 60, "2026-10-12 09:00:00"
        )

        sessions = temp_db.get_study_sessions(user_id)
        assert [s["topic"] for s in sessions] == ["Newer id", "Older id"]


class TestSQLInjectionSafety:
    def test_injection_string_stored_as_plain_text(self, temp_db):
        user_id = _demo_user(temp_db)
        subject_id = temp_db.add_subject(user_id, "Mathematics")
        malicious = "x'); DROP TABLE study_sessions;--"

        temp_db.add_study_session(
            user_id=user_id,
            subject_id=subject_id,
            topic=malicious,
            duration_minutes=30,
        )

        sessions = temp_db.get_study_sessions(user_id)
        assert len(sessions) == 1
        assert sessions[0]["topic"] == malicious
        assert temp_db.get_total_study_sessions(user_id) == 1