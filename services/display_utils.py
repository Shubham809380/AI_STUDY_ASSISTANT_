"""Small pure helpers for study-session validation and display.

These functions do not import Streamlit so they can be unit tested in
isolation.  Validation stays here so the UI can call the same checks that
pytest exercises.
"""

from datetime import date, datetime, time
from typing import List, Optional

MAX_TOPIC_LENGTH = 100
MAX_DURATION_MINUTES = 600
MAX_SUBJECT_LENGTH = 50

_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d",
)


def validate_study_session_input(
    topic: Optional[str],
    duration: Optional[int],
    max_duration: int = MAX_DURATION_MINUTES,
) -> Optional[str]:
    """Return a friendly error message for invalid input, else ``None``."""
    if not topic or not topic.strip():
        return "Please enter the topic you studied."

    if duration is None:
        return "Duration must be a positive number of minutes."

    if duration < 1:
        return "Duration must be at least 1 minute."

    if duration > max_duration:
        return f"Duration must be {max_duration} minutes or less."

    return None


def normalize_study_topic(
    topic: Optional[str],
    max_length: int = MAX_TOPIC_LENGTH,
) -> str:
    """Strip surrounding whitespace and truncate a topic to ``max_length``."""
    cleaned = topic.strip() if topic else ""
    return cleaned[:max_length]


def capitalize_topic(topic: str) -> str:
    """Return ``topic`` with only its first letter capitalized."""
    if not topic:
        return topic
    return topic[:1].upper() + topic[1:]


def format_timestamp(value):
    """Format a timestamp as '15 Aug 2026, 1:02 PM'.

    Accepts ``datetime``/``date`` objects or common string formats.  If the
    value cannot be parsed, the raw value is returned unchanged.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time(0, 0))
    elif isinstance(value, str):
        text = value.strip()
        parsed = None

        for fmt in _TIMESTAMP_FORMATS:
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

        if parsed is None:
            return value
    else:
        return value

    hour_12 = parsed.hour % 12 or 12
    ampm = "AM" if parsed.hour < 12 else "PM"

    return (
        f"{parsed.day} {parsed.strftime('%b %Y')}, "
        f"{hour_12}:{parsed.strftime('%M')} {ampm}"
    )


def session_subject_label(subject_name: Optional[str]) -> str:
    """Return a display label for a session's subject name."""
    return subject_name if subject_name else "No Subject"


def study_session_subjects(sessions) -> List[str]:
    """Return the sorted, unique subject labels present in ``sessions``."""
    labels = {
        session_subject_label(session["subject_name"])
        for session in sessions
    }
    return sorted(labels)


def filter_study_sessions(sessions, subject: str):
    """Return sessions whose subject label equals ``subject``.

    ``subject`` equal to ``"All"`` (or empty) returns every session.
    """
    if not subject or subject == "All":
        return list(sessions)

    return [
        session
        for session in sessions
        if session_subject_label(session["subject_name"]) == subject
    ]


def normalize_subject_name(
    name: Optional[str],
    max_length: int = MAX_SUBJECT_LENGTH,
) -> str:
    """Strip surrounding whitespace from a subject name (no truncation).

    Subject names that are too long are rejected by ``validate_subject_name``
    rather than silently cut off.
    """
    return name.strip() if name else ""


def validate_subject_name(
    name: Optional[str],
    existing_names: Optional[List[str]] = None,
    max_length: int = MAX_SUBJECT_LENGTH,
) -> Optional[str]:
    """Return a friendly error message for an invalid subject name, else ``None``.

    Checks that the trimmed name is non-empty, at most ``max_length``
    characters, and does not duplicate an existing subject (ignoring case).
    """
    cleaned = normalize_subject_name(name)

    if not cleaned:
        return "Please enter a subject name."

    if len(cleaned) > max_length:
        return (
            f"Subject name must be {max_length} characters or fewer."
        )

    cleaned_lower = cleaned.lower()

    for existing in existing_names or []:
        if (existing or "").strip().lower() == cleaned_lower:
            return "That subject already exists."

    return None