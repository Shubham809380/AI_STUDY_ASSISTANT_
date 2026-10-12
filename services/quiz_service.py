import json
import re

from services.llm_service import ask_llm
from services.output_validator import MAX_GENERATION_ATTEMPTS, validate_quiz_data


def _strip_code_fences(response: str) -> str:
    """Remove accidental markdown code fences around a JSON response."""
    cleaned = response.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()


def _parse_json_response(response: str):
    """Parse a JSON response, tolerating accidental code fences."""
    phantom = response.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", phantom, re.DOTALL)
    if fence:
        phantom = fence.group(1)

    try:
        return json.loads(_strip_code_fences(phantom))
    except json.JSONDecodeError:
        return None


def _build_quiz_prompt(
    topic: str,
    number_of_questions: int,
    difficulty: str,
    feedback: str,
) -> str:
    feedback_section = ""
    if feedback:
        feedback_section = (
            "\nYour previous response was invalid and was rejected:\n"
            f"{feedback}\n"
            "Fix every listed issue and return ONLY valid JSON that matches "
            "the required structure exactly."
        )

    return f"""
You are an AI quiz generator for college students.

Create a multiple-choice quiz.

Topic:
{topic}

Number of Questions:
{number_of_questions}

Difficulty:
{difficulty}

Return ONLY valid JSON.

The JSON must have this exact structure:

{{
    "questions": [
        {{
            "question": "Question text",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "correct_answer": "A",
            "explanation": "Short explanation"
        }}
    ]
}}

Rules:
- Generate exactly {number_of_questions} questions.
- Each question must have a clear question statement.
- Each question must have exactly four non-empty options labelled A, B, C, D.
- correct_answer must be one of A, B, C, or D and must match one of the options.
- Make questions educational and relevant to the topic and difficulty.
- Do not include markdown.
- Return JSON only.
{feedback_section}
"""


def generate_quiz(
    topic: str,
    number_of_questions: int = 5,
    difficulty: str = "Medium",
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
):
    """Generate a validated multiple-choice quiz with bounded retries.

    Each generated quiz is validated so every MCQ has a question, exactly four
    options and a valid correct answer.  Invalid output is regenerated with
    corrective feedback up to ``max_attempts`` times.  If validation still
    fails, a clear ``ValueError`` is raised (never silently returned).
    """
    if not topic.strip():
        raise ValueError("Topic cannot be empty.")

    if number_of_questions < 1:
        raise ValueError("Number of questions must be at least 1.")

    attempts = 0
    feedback = ""
    last_issues = []

    while attempts < max_attempts:
        attempts += 1

        prompt = _build_quiz_prompt(
            topic, number_of_questions, difficulty, feedback
        )
        response = (ask_llm(prompt) or "").strip()

        quiz_data = _parse_json_response(response)
        if quiz_data is None:
            last_issues = ["The LLM response was not valid JSON."]
            feedback = "Your previous response was not valid JSON. Return ONLY a valid JSON object."
            continue

        last_issues = validate_quiz_data(quiz_data, number_of_questions)
        if not last_issues:
            return quiz_data

        feedback = "; ".join(last_issues)

    raise ValueError(
        f"Unable to produce a valid quiz after {attempts} attempt(s): "
        + "; ".join(last_issues)
    )