"""Tests for the validated structured study-material generator."""

import pytest

from services.notes_service import (
    MAX_GENERATION_ATTEMPTS,
    format_study_mcqs_for_display,
    generate_notes,
    generate_study_material,
)
from tests.testdata import INVALID_STUDY_TEXT, VALID_STUDY_TEXT


@pytest.fixture
def fake_llm_valid(monkeypatch):
    def _fake(prompt):
        return VALID_STUDY_TEXT
    monkeypatch.setattr("services.notes_service.ask_llm", _fake)


@pytest.fixture
def fake_llm_invalid(monkeypatch):
    def _fake(prompt):
        return INVALID_STUDY_TEXT
    monkeypatch.setattr("services.notes_service.ask_llm", _fake)


@pytest.fixture
def fake_llm_empty(monkeypatch):
    def _fake(prompt):
        return ""
    monkeypatch.setattr("services.notes_service.ask_llm", _fake)


def make_sequential_fake(responses):
    state = {"index": 0}

    def _fake(prompt):
        response = responses[min(state["index"], len(responses) - 1)]
        state["index"] += 1
        return response

    return _fake


@pytest.fixture
def fake_llm_recovers(monkeypatch):
    fake = make_sequential_fake(
        [INVALID_STUDY_TEXT, INVALID_STUDY_TEXT, VALID_STUDY_TEXT]
    )
    monkeypatch.setattr("services.notes_service.ask_llm", fake)
    return fake


class TestGenerateStudyMaterial:
    def test_valid_output_returned(self, fake_llm_valid):
        result = generate_study_material("Artificial Intelligence", "Beginner")
        assert result.status == "valid"
        assert result.validation.is_valid is True
        assert result.attempts == 1
        assert result.text

    def test_verification_notice_appended(self, fake_llm_valid):
        result = generate_study_material("Artificial Intelligence", "Beginner")
        assert "AI-generated study content may contain errors" in result.text

    def test_incomplete_never_marked_valid(self, fake_llm_invalid):
        result = generate_study_material("Cloud Computing", "Intermediate")
        assert result.status == "incomplete"
        assert result.validation.is_valid is False
        assert result.attempts == MAX_GENERATION_ATTEMPTS

    def test_regeneration_until_valid_is_bounded(self, fake_llm_recovers):
        result = generate_study_material("Web Development", "Beginner")
        assert result.attempts == 3
        assert result.status == "valid"

    def test_empty_response_is_bounded(self, fake_llm_empty):
        result = generate_study_material("Data Analytics", "Intermediate")
        assert result.status == "incomplete"
        assert result.attempts == MAX_GENERATION_ATTEMPTS
        assert "empty" in result.message.lower()

    def test_custom_max_attempts_respected(self, monkeypatch):
        calls = {"count": 0}

        def _fake(prompt):
            calls["count"] += 1
            return INVALID_STUDY_TEXT

        monkeypatch.setattr("services.notes_service.ask_llm", _fake)
        result = generate_study_material(
            "Cybersecurity", "Advanced", max_attempts=2
        )
        assert result.attempts == 2
        assert calls["count"] == 2
        assert result.status == "incomplete"

    def test_empty_topic_rejected(self, fake_llm_valid):
        with pytest.raises(ValueError):
            generate_study_material("   ")


class TestFiveRequiredTopics:
    @pytest.mark.parametrize(
        "topic,level",
        [
            ("Artificial Intelligence", "Beginner"),
            ("Cloud Computing", "Intermediate"),
            ("Data Analytics", "Intermediate"),
            ("Cybersecurity", "Advanced"),
            ("Web Development", "Beginner"),
        ],
    )
    def test_five_topics_produce_valid_structure(self, fake_llm_valid, topic, level):
        result = generate_study_material(topic, level)
        assert result.status == "valid"
        validation = result.validation
        assert len(validation.important_points) == 5
        assert len(validation.practice_questions) == 5
        assert len(validation.mcqs) == 5
        for mcq in validation.mcqs:
            assert mcq.question.strip()
            assert set(mcq.options.keys()) == {"A", "B", "C", "D"}
            assert all(mcq.options[k].strip() for k in ("A", "B", "C", "D"))
            assert mcq.correct_answer in {"A", "B", "C", "D"}


class TestGenerateNotesCompatibility:
    def test_generate_notes_returns_markdown_text(self, fake_llm_valid):
        text = generate_notes(
            "Artificial Intelligence",
            study_material="",
            learner_level="Beginner",
        )
        assert isinstance(text, str)
        assert "## Explanation" in text


class TestTopicGuidanceInPrompt:
    def _capture_prompt(self, monkeypatch, topic, level="Intermediate"):
        captured = {}

        def _fake(prompt):
            captured["prompt"] = prompt
            return VALID_STUDY_TEXT

        monkeypatch.setattr("services.notes_service.ask_llm", _fake)
        generate_study_material(topic, level, max_attempts=1)
        return captured["prompt"]

    def test_data_analytics_guidance_in_prompt(self, monkeypatch):
        prompt = self._capture_prompt(
            monkeypatch, "Explain Data Analytics for an intermediate learner"
        )
        assert "Data Analytics topic accuracy" in prompt
        assert "four analytics types" in prompt
        assert "descriptive" in prompt
        assert "diagnostic" in prompt
        assert "predictive" in prompt
        assert "prescriptive" in prompt
        assert "significant share of the effort" in prompt
        assert "Do not claim data preprocessing typically consumes the majority" in prompt

    def test_web_development_guidance_in_prompt(self, monkeypatch):
        prompt = self._capture_prompt(monkeypatch, "Web Development", "Beginner")
        assert "Web Development topic accuracy" in prompt
        assert "actual question statement" in prompt
        assert "HTML" in prompt
        assert "CSS" in prompt
        assert "JavaScript" in prompt

    def test_case_insensitive_topic_matching(self, monkeypatch):
        prompt = self._capture_prompt(
            monkeypatch, "explain data analytics for an intermediate learner"
        )
        assert "Data Analytics topic accuracy" in prompt

    def test_machine_learning_uses_ai_guidance(self, monkeypatch):
        prompt = self._capture_prompt(monkeypatch, "Machine Learning", "Beginner")
        assert "Artificial Intelligence topic accuracy" in prompt
        assert "machine learning as a subset of artificial intelligence" in prompt.lower()


class TestRegeneration:
    def test_first_invalid_then_valid_exactly_two_calls(self, monkeypatch):
        responses = [INVALID_STUDY_TEXT, VALID_STUDY_TEXT]
        calls = {"count": 0}

        def _fake(prompt):
            response = responses[min(calls["count"], len(responses) - 1)]
            calls["count"] += 1
            return response

        monkeypatch.setattr("services.notes_service.ask_llm", _fake)
        result = generate_study_material("Data Analytics", "Intermediate")
        assert calls["count"] == 2
        assert result.attempts == 2
        assert result.status == "valid"

    def test_always_invalid_stops_at_max_attempts(self, monkeypatch):
        calls = {"count": 0}

        def _fake(prompt):
            calls["count"] += 1
            return INVALID_STUDY_TEXT

        monkeypatch.setattr("services.notes_service.ask_llm", _fake)
        result = generate_study_material("Web Development", "Beginner")
        assert result.status == "incomplete"
        assert calls["count"] == MAX_GENERATION_ATTEMPTS
        assert result.attempts == MAX_GENERATION_ATTEMPTS

    def test_overclaim_warning_included_in_regeneration_feedback(self, monkeypatch):
        invalid = VALID_STUDY_TEXT.replace(
            "## Explanation",
            "## Explanation\nAI always understands everything students read.",
        )
        invalid = invalid.replace("5. Give one everyday example of AI.", "")
        prompts = []

        def _fake(prompt):
            prompts.append(prompt)
            return VALID_STUDY_TEXT if len(prompts) > 1 else invalid

        monkeypatch.setattr("services.notes_service.ask_llm", _fake)
        generate_study_material("Data Analytics", "Intermediate")
        assert len(prompts) == 2
        assert "Non-blocking quality suggestions" in prompts[1]
        assert "'always'" in prompts[1]


class TestMcqDisplayFormatting:
    def test_each_option_is_on_its_own_line(self, valid_study_text):
        formatted = format_study_mcqs_for_display(valid_study_text)
        option_lines = [
            line
            for line in formatted.split("\n")
            if line.startswith(("- A. ", "- B. ", "- C. ", "- D. "))
        ]
        assert len(option_lines) == 20

    def test_question_text_and_correct_answer_present(self, valid_study_text):
        formatted = format_study_mcqs_for_display(valid_study_text)
        assert "**MCQ 1.**" in formatted
        assert "Which statement best describes Machine Learning?" in formatted
        assert formatted.count("Correct Answer:") == 5

    def test_other_sections_preserved(self, valid_study_text):
        formatted = format_study_mcqs_for_display(valid_study_text)
        assert "## Explanation" in formatted
        assert "## Short Summary" in formatted
        assert "## Important Points" in formatted
        assert "## Practice Questions" in formatted

    def test_display_preserves_verification_notice_once(self):
        text = (
            VALID_STUDY_TEXT
            + "\n\n---\n\n"
            + "*Note: AI-generated study content may contain errors. "
            + "Verify important information.*"
        )
        formatted = format_study_mcqs_for_display(text)
        assert formatted.count("may contain errors") == 1


class TestVerificationNotice:
    def test_notice_appended_once_when_missing(self, fake_llm_valid):
        result = generate_study_material("Artificial Intelligence", "Beginner")
        assert result.text.count("may contain errors") == 1

    def test_notice_not_duplicated_when_present(self, fake_llm_recovers):
        from services.notes_service import _append_verification_notice

        text = "Content.\n\nNote: AI-generated study content may contain errors."
        assert _append_verification_notice(text).count("may contain errors") == 1
        assert _append_verification_notice(text).rstrip().endswith("errors.")