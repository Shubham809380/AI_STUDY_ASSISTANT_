"""Tests for the validated quiz generator with bounded retries."""

import json

import pytest

from services.output_validator import validate_quiz_data
from services.quiz_service import generate_quiz
from tests.testdata import make_valid_quiz


BAD_QUIZ = {
    "questions": [
        {
            "question": "",
            "options": {"A": "one", "B": "two", "C": "three"},
            "correct_answer": "Z",
            "explanation": "",
        }
        for _ in range(5)
    ]
}


@pytest.fixture
def fake_llm_valid_quiz(monkeypatch):
    payload = json.dumps(make_valid_quiz(5))
    monkeypatch.setattr(
        "services.quiz_service.ask_llm", lambda prompt: payload
    )


@pytest.fixture
def fake_llm_recovers_quiz(monkeypatch):
    valid = json.dumps(make_valid_quiz(5))
    responses = [json.dumps(BAD_QUIZ), valid]
    state = {"index": 0}

    def _fake(prompt):
        response = responses[min(state["index"], len(responses) - 1)]
        state["index"] += 1
        return response

    monkeypatch.setattr("services.quiz_service.ask_llm", _fake)
    return state


@pytest.fixture
def fake_llm_always_bad(monkeypatch):
    calls = {"count": 0}

    def _fake(prompt):
        calls["count"] += 1
        return json.dumps(BAD_QUIZ)

    monkeypatch.setattr("services.quiz_service.ask_llm", _fake)
    return calls


@pytest.fixture
def fake_llm_not_json(monkeypatch):
    monkeypatch.setattr(
        "services.quiz_service.ask_llm", lambda prompt: "not json at all"
    )


class TestGenerateQuiz:
    def test_valid_quiz_returned(self, fake_llm_valid_quiz):
        quiz = generate_quiz("Python", 5, "Medium")
        assert len(quiz["questions"]) == 5
        assert validate_quiz_data(quiz, expected_count=5) == []

    def test_invalid_mcq_regenerates_to_valid(self, fake_llm_recovers_quiz):
        quiz = generate_quiz("Python", 5, "Medium")
        assert len(quiz["questions"]) == 5
        assert validate_quiz_data(quiz, expected_count=5) == []

    def test_malformed_json_regenerates(self, monkeypatch):
        valid = json.dumps(make_valid_quiz(3))
        responses = ["not json", valid]
        state = {"index": 0}

        def _fake(prompt):
            response = responses[min(state["index"], len(responses) - 1)]
            state["index"] += 1
            return response

        monkeypatch.setattr("services.quiz_service.ask_llm", _fake)
        quiz = generate_quiz("Python", 3, "Easy", max_attempts=3)
        assert len(quiz["questions"]) == 3

    def test_retries_are_bounded_and_raise(self, fake_llm_always_bad):
        with pytest.raises(ValueError) as exc_info:
            generate_quiz("Python", 5, "Medium", max_attempts=3)
        assert fake_llm_always_bad["count"] == 3
        assert "after 3 attempt(s)" in str(exc_info.value)

    def test_empty_topic_rejected(self, fake_llm_valid_quiz):
        with pytest.raises(ValueError):
            generate_quiz("   ", 5, "Medium")

    def test_wrong_question_count_regenerates(self, monkeypatch):
        valid = json.dumps(make_valid_quiz(5))
        wrong = json.dumps(make_valid_quiz(2))
        responses = [wrong, valid]
        state = {"index": 0}

        def _fake(prompt):
            response = responses[min(state["index"], len(responses) - 1)]
            state["index"] += 1
            return response

        monkeypatch.setattr("services.quiz_service.ask_llm", _fake)
        quiz = generate_quiz("Python", 5, "Medium")
        assert len(quiz["questions"]) == 5