"""Tests for the five-section output validator and cleanup helpers."""

import pytest

from services.output_validator import (
    MCQ,
    EXPECTED_IMPORTANT_POINTS,
    EXPECTED_MCQS,
    EXPECTED_PRACTICE_QUESTIONS,
    clean_terminology,
    detect_overclaim_warnings,
    find_duplicate_items,
    parse_mcqs,
    remove_stray_artifacts,
    repair_known_artifacts,
    validate_mcq,
    validate_mcqs,
    validate_quiz_data,
    validate_study_output,
)


class TestStructureValidator:
    def test_valid_output_passes(self, valid_study_text):
        result = validate_study_output(valid_study_text)
        assert result.is_valid is True
        assert result.issues == []

    def test_all_five_sections_are_present(self, valid_study_text):
        result = validate_study_output(valid_study_text)
        assert result.explanation.strip()
        assert result.summary.strip()
        assert len(result.important_points) == EXPECTED_IMPORTANT_POINTS
        assert len(result.practice_questions) == EXPECTED_PRACTICE_QUESTIONS
        assert len(result.mcqs) == EXPECTED_MCQS

    def test_invalid_output_is_not_marked_valid(self, invalid_study_text):
        result = validate_study_output(invalid_study_text)
        assert result.is_valid is False
        assert result.issues

    def test_missing_section_is_detected(self, valid_study_text):
        marker = "## Short Summary\nAI is a broad field. ML is a subset of AI. AI systems are tools that\napproximate tasks instead of thinking exactly like humans."
        text = valid_study_text.replace(marker, "")
        result = validate_study_output(text)
        assert result.is_valid is False
        assert any("Short Summary" in issue for issue in result.issues)

    def test_wrong_important_points_count(self, valid_study_text):
        text = valid_study_text.replace("5. Give one everyday example of AI.", "")
        result = validate_study_output(text)
        assert result.is_valid is False
        assert any("Exactly 5" in issue or "exactly 5" in issue
                   for issue in result.issues)

    def test_wrong_mcq_count(self, valid_study_text):
        cut = valid_study_text.split("**Q5.**")[0]
        result = validate_study_output(cut)
        assert result.is_valid is False
        assert any("exactly 5 questions" in issue for issue in result.issues)

    def test_duplicate_headings_detected(self, invalid_study_text):
        result = validate_study_output(invalid_study_text)
        assert "MCQs" in result.duplicate_headings

    def test_duplicate_points_detected(self, invalid_study_text):
        result = validate_study_output(invalid_study_text)
        assert any("Duplicate Important Points" in issue for issue in result.issues)

    def test_inconsistent_numbering_detected(self, valid_study_text):
        text = valid_study_text.replace(
            "2. Machine Learning is a subset of Artificial Intelligence.",
            "4. Machine Learning is a subset of Artificial Intelligence.",
        )
        result = validate_study_output(text)
        assert any("Numbered list" in issue for issue in result.issues)

    @pytest.mark.parametrize("count", [4, 6])
    def test_wrong_important_points_count_rejected(self, valid_study_text, count):
        points = "\n".join(f"{i}. point {i}" for i in range(1, count + 1))
        text = valid_study_text.split("## Important Points")[0] + (
            f"## Important Points\n{points}"
        ) + valid_study_text.split("## Practice Questions")[1]
        result = validate_study_output(text)
        assert result.is_valid is False
        assert any("Important Points" in issue for issue in result.issues)

    @pytest.mark.parametrize("count", [4, 6])
    def test_wrong_practice_question_count_rejected(self, valid_study_text, count):
        questions = "\n".join(f"{i}. question {i}?" for i in range(1, count + 1))
        text = valid_study_text.split("## Practice Questions")[0] + (
            f"## Practice Questions\n{questions}"
        ) + valid_study_text.split("## MCQs")[1]
        result = validate_study_output(text)
        assert result.is_valid is False
        assert any("Practice Questions" in issue for issue in result.issues)

    @pytest.mark.parametrize("count", [4, 6])
    def test_wrong_mcq_count_rejected(self, valid_study_text, count):
        blocks = []
        for index in range(1, count + 1):
            blocks.append(
                f"**Q{index}.** Question {index}?\n"
                "A. one\nB. two\nC. three\nD. four\n"
                f"Correct Answer: A"
            )
        mcqs = "\n\n".join(blocks)
        text = valid_study_text.split("## MCQs")[0] + f"## MCQs\n{mcqs}"
        result = validate_study_output(text)
        assert result.is_valid is False
        assert any("MCQs must contain exactly 5" in issue for issue in result.issues)


class TestMCQValidator:
    def test_valid_mcq_passes(self):
        mcq = MCQ(
            question="Which option?",
            options={"A": "one", "B": "two", "C": "three", "D": "four"},
            correct_answer="B",
        )
        assert validate_mcq(mcq) == []

    def test_missing_option_detected(self):
        mcq = MCQ(
            question="Which option?",
            options={"A": "one", "B": "two", "C": "three", "D": ""},
            correct_answer="B",
        )
        issues = validate_mcq(mcq, index=1)
        assert any("option D is empty" in issue for issue in issues)

    def test_invalid_correct_answer_detected(self):
        mcq = MCQ(
            question="Which option?",
            options={"A": "one", "B": "two", "C": "three", "D": "four"},
            correct_answer="E",
        )
        issues = validate_mcq(mcq, index=1)
        assert any("must be one of A, B, C, or D" in issue for issue in issues)

    def test_missing_question_statement_rejected(self):
        mcq = MCQ(
            question="",
            options={"A": "one", "B": "two", "C": "three", "D": "four"},
            correct_answer="A",
        )
        issues = validate_mcq(mcq, index=1)
        assert any("missing question statement" in issue for issue in issues)

    def test_fewer_than_four_options_rejected(self):
        mcq = MCQ(
            question="Which option?",
            options={"A": "one", "B": "two", "C": "three"},
            correct_answer="A",
        )
        issues = validate_mcq(mcq, index=1)
        assert any("missing option(s): D" in issue for issue in issues)

    def test_parse_mcqs_from_text(self, valid_study_text):
        result = validate_study_output(valid_study_text)
        assert len(result.mcqs) == EXPECTED_MCQS
        assert all(mcq.options.keys() == {"A", "B", "C", "D"} for mcq in result.mcqs)

    def test_trailing_text_after_answer_is_ignored(self):
        text = (
            "## Explanation\nsample\n\n## Short Summary\nsample\n"
            "## Important Points\n1. a\n2. b\n3. c\n4. d\n5. e\n\n"
            "## Practice Questions\n1. q1\n2. q2\n3. q3\n4. q4\n5. q5\n\n"
            "## MCQs\n"
            "**Q1.** Which option?\n"
            "A. one\nB. two\nC. three\nD. four\n"
            "Correct Answer: B\n"
            "Note: AI-generated study content may contain errors.\n"
        )
        result = validate_study_output(text)
        assert len(result.mcqs) == 1
        assert result.mcqs[0].question == "Which option?"
        assert "may contain errors" not in result.mcqs[0].question


class TestQuizDataValidator:
    def test_valid_quiz_passes(self, valid_quiz):
        assert validate_quiz_data(valid_quiz, expected_count=5) == []

    def test_wrong_question_count_detected(self, valid_quiz):
        quiz = valid_quiz.copy()
        quiz["questions"] = quiz["questions"][:3]
        issues = validate_quiz_data(quiz, expected_count=5)
        assert any("exactly 5 questions" in issue for issue in issues)

    def test_invalid_mcq_within_quiz_detected(self, valid_quiz):
        quiz = valid_quiz.copy()
        quiz["questions"][0]["options"]["D"] = ""
        issues = validate_quiz_data(quiz, expected_count=5)
        assert any("option D is empty" in issue for issue in issues)

    def test_non_json_input_rejected(self):
        assert validate_quiz_data("not a dict") != []


class TestDuplicateDetection:
    def test_find_duplicate_items(self):
        items = ["One point.", "one point.", "Second.", "Second."]
        duplicates = find_duplicate_items(items)
        assert "one point" in duplicates
        assert "second" in duplicates


class TestCleanup:
    def test_terminology_standardization(self):
        cleaned = clean_terminology(
            "artificial intelligence relies on Iaas, PaaS and SaaS; "
            "zero trust architecture uses tls 1.3"
        )
        assert "Artificial Intelligence" in cleaned
        assert "IaaS" in cleaned
        assert "PaaS" in cleaned
        assert "SaaS" in cleaned
        assert "Zero Trust Architecture" in cleaned
        assert "TLS 1.3" in cleaned

    def test_stray_c2_artifact_removed(self):
        assert "c2" not in remove_stray_artifacts("stray token c2 here")

    def test_replacement_character_removed(self):
        cleaned = remove_stray_artifacts("Zero Trust\u2014specifically \ufffd here")
        assert "\ufffd" not in cleaned
        assert "Zero Trust" in cleaned

    def test_repair_combines_cleanups(self):
        text = "artificial intelligence\n## ## c2 IAAS"
        cleaned = repair_known_artifacts(text)
        assert "Artificial Intelligence" in cleaned
        assert "IaaS" in cleaned
        assert "c2" not in cleaned

    def test_malformed_heading_fixed(self):
        from services.output_validator import normalize_headings
        assert normalize_headings("## ## Explanation:") == "## Explanation"

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("IaaS is the acronym", "IaaS is the acronym"),
            ("Iaas is the acronym", "IaaS is the acronym"),
            ("laaS is the acronym", "IaaS is the acronym"),
            ("PaaS is the acronym", "PaaS is the acronym"),
            ("Paas is the acronym", "PaaS is the acronym"),
            ("SaaS is the acronym", "SaaS is the acronym"),
            ("Saas is the acronym", "SaaS is the acronym"),
            ("Tls 1.3 is modern", "TLS 1.3 is modern"),
            ("zero trust architecture matters", "Zero Trust Architecture matters"),
        ],
    )
    def test_repair_normalizes_terminology(self, raw, expected):
        assert repair_known_artifacts(raw) == expected

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("A.I. is a broad field", "AI is a broad field"),
            ("a.i. is a broad field", "AI is a broad field"),
            ("Ai is a broad field", "AI is a broad field"),
        ],
    )
    def test_repair_normalizes_ai_acronym(self, raw, expected):
        assert repair_known_artifacts(raw) == expected

    def test_multiple_ai_spellings_apply_once(self):
        cleaned = repair_known_artifacts("A.I. and AI and ai both refer to AI")
        assert cleaned.count("AI") == 4

    def test_repair_fixes_double_hash_heading(self):
        assert repair_known_artifacts("## ## Heading:") == "## Heading"
        assert repair_known_artifacts("## ## Heading") == "## Heading"

    def test_repair_idempotent(self):
        text = (
            "Iaas, laaS, Paas, Saas, A.I., ai, Tls 1.3,\n"
            "zero trust architecture, c2, ## ## Heading"
        )
        once = repair_known_artifacts(text)
        twice = repair_known_artifacts(once)
        assert twice == once

    def test_words_containing_ai_not_modified(self):
        text = "again pain brain mountain fail sail"
        assert repair_known_artifacts(text) == text

    def test_repair_removes_c2_artifact(self):
        cleaned = repair_known_artifacts("intro text c2 c2 more text")
        assert "c2" not in cleaned


class TestOverclaimWarnings:
    def test_risky_phrases_detected(self):
        text = (
            "The system always works. It never fails. "
            "AI thinks like a human and AI understands everything. "
            "Cleaning typically consumes the majority of effort."
        )
        warnings = detect_overclaim_warnings(text)
        assert any("'always'" in warning for warning in warnings)
        assert any("'never fails'" in warning for warning in warnings)
        assert any("'AI thinks like a human'" in warning for warning in warnings)
        assert any("'AI understands'" in warning for warning in warnings)
        assert any("'typically consumes the majority'" in warning for warning in warnings)

    def test_clean_text_has_no_warnings(self, valid_study_text):
        assert detect_overclaim_warnings(valid_study_text) == []

    def test_warnings_not_attached_to_valid_output(self, valid_study_text):
        warnings = detect_overclaim_warnings(valid_study_text)
        assert warnings == []

    def test_overclaims_do_not_cause_validation_failure(self, valid_study_text):
        text = valid_study_text + "\n\nAI understands everything. It always works."
        result = validate_study_output(text)
        assert result.is_valid is True
        assert result.warnings
        assert any("'AI understands'" in warning for warning in result.warnings)
        assert any("'always'" in warning for warning in result.warnings)

    def test_overclaims_do_not_appear_in_issues(self, valid_study_text):
        text = valid_study_text + "\n\nThe system never fails."
        result = validate_study_output(text)
        assert all("claim" not in issue.lower() for issue in result.issues)