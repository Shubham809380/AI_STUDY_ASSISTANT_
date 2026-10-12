import re
from dataclasses import dataclass, field

from services.llm_service import ask_llm
from services.output_validator import (
    MAX_GENERATION_ATTEMPTS,
    VERIFICATION_NOTICE,
    StudyValidationResult,
    extract_sections,
    parse_mcqs,
    repair_known_artifacts,
    validate_study_output,
)


@dataclass
class StudyMaterialResult:
    """Result of a structured study-material generation attempt."""

    status: str
    topic: str
    learner_level: str
    text: str
    validation: StudyValidationResult = field(default=None)
    attempts: int = 0
    message: str = ""


# ---------------------------------------------------------------------------
# Topic-specific accuracy guidance (avoids unsupported universal claims).
# ---------------------------------------------------------------------------

TOPIC_GUIDANCE = {
    "ai": (
        "Artificial Intelligence topic accuracy:\n"
        "- Explain machine learning as a subset of artificial intelligence. "
        "AI is the broader field (it also includes search, knowledge "
        "representation, planning, NLP, and computer vision); ML is the branch "
        "that learns patterns from data.\n"
        "- Do not state that AI necessarily thinks, understands, or reasons "
        "exactly like a human. Use careful wording such as 'the model is not "
        "conscious' and describe systems as tools that approximate tasks.\n"
    ),
    "cloud": (
        "Cloud Computing topic accuracy:\n"
        "- Define IaaS as providing virtualized compute, storage and network; "
        "PaaS as a managed platform for building and deploying applications; "
        "SaaS as complete applications delivered over the internet.\n"
        "- Distinguish deployment models (public, private, hybrid, community) "
        "precisely. Describe elasticity as scaling resources up and down "
        "automatically in response to demand.\n"
        "- Explain shared responsibility according to the specific provider "
        "and service model (for example, AWS, Azure, and Google Cloud split "
        "platform versus customer responsibilities differently for IaaS, "
        "PaaS, and SaaS).\n"
        "- Avoid unsupported universal claims about hybrid-cloud capabilities; "
        "state that they vary by provider, design, and implementation.\n"
    ),
    "analytics": (
        "Data Analytics topic accuracy:\n"
        "- Present the analytics lifecycle in distinct, non-repeated stages "
        "(for example: define the problem, collect data, clean and prepare "
        "data, analyze or model, interpret and communicate, then act or "
        "iterate). Do not repeat the same stage under different names.\n"
        "- Describe the four analytics types accurately: descriptive (what "
        "happened), diagnostic (why it happened), predictive (what is likely "
        "to happen), and prescriptive (what action to take).\n"
        "- Do not claim data preprocessing typically consumes the majority of "
        "an analyst's time. Use qualified wording such as 'cleaning and "
        "preparing data can take a significant share of the effort depending "
        "on the project and data quality'.\n"
    ),
    "cyber": (
        "Cybersecurity topic accuracy:\n"
        "- Use precise terminology in the NIST SP 800-207 Zero Trust "
        "Architecture context: the Policy Decision Point (PDP) evaluates "
        "policy and makes access decisions; the Policy Engine is the component "
        "of the PDP that renders those decisions. Distinguish the PDP from the "
        "Policy Administrator.\n"
        "- Qualify TLS 1.3 forward secrecy: handshakes that use ephemeral key "
        "exchange provide forward secrecy, but pre-shared-key (PSK-only) and "
        "0-RTT early-data modes do not provide forward secrecy for the "
        "pre-shared key or early data.\n"
        "- Do not overstate the guarantees of a single security control "
        "(a control reduces risk; it does not by itself make a system secure).\n"
    ),
    "web": (
        "Web Development topic accuracy:\n"
        "- Keep HTML (structure and content), CSS (presentation and layout), "
        "and JavaScript (behavior and interactivity) definitions accurate, "
        "along with frontend, backend, and full-stack terminology.\n"
        "- Ensure every MCQ contains an actual question statement (never leave "
        "the question blank), exactly four options A-D, and one correct "
        "answer.\n"
    ),
    "general": (
        "General accuracy and formatting rules:\n"
        "- Use consistent spelling and capitalization: Artificial Intelligence, "
        "Infrastructure as a Service (IaaS), Platform as a Service (PaaS), "
        "Software as a Service (SaaS), Zero Trust Architecture, and Transport "
        "Layer Security (TLS) 1.3.\n"
        "- Do not add stray text, duplicate sections, or formatting artifacts.\n"
    ),
}


def _classify_topic(topic: str) -> str:
    lowered = topic.lower()

    if "artificial intelligence" in lowered or "machine learning" in lowered:
        return "ai"
    if "cloud" in lowered:
        return "cloud"
    if "data analytics" in lowered or "analytics" in lowered:
        return "analytics"
    if any(
        word in lowered
        for word in ("cyber", "zero trust", "nist", "tls", "security")
    ):
        return "cyber"
    if any(
        word in lowered
        for word in ("web", "html", "css", "javascript", "full-stack")
    ):
        return "web"
    return "general"


def _build_accuracy_guidance(topic: str) -> str:
    guidance = [_build_topic_guidance(topic)]
    general = TOPIC_GUIDANCE["general"]
    if general not in guidance:
        guidance.append(general)
    return "\n".join(part for part in guidance if part)


def _build_topic_guidance(topic: str) -> str:
    klass = _classify_topic(topic)
    return TOPIC_GUIDANCE.get(klass, "")


def _append_verification_notice(text: str) -> str:
    """Append the verification notice only if an equivalent reminder is absent.

    The LLM sometimes adds its own verification sentence, so we accept any
    phrasing that mentions that generated content may contain errors.  This
    prevents duplicate notices.
    """
    if not text:
        return VERIFICATION_NOTICE + "\n"
    if re.search(r"may contain errors", text, re.IGNORECASE):
        return text
    return text.rstrip() + "\n" + VERIFICATION_NOTICE + "\n"


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_study_prompt(
    topic: str,
    learner_level: str,
    study_material: str,
    feedback: str,
) -> str:
    material_section = ""
    if study_material and study_material.strip():
        material_section = f"Study Material:\n{study_material}\n"

    feedback_section = ""
    if feedback:
        feedback_section = (
            "\nYour previous response was invalid for these reasons:\n"
            f"{feedback}\n"
            "Fix every listed issue and return ONLY the corrected "
            "five-section output using the exact template."
        )

    return f"""
You are an expert educational AI study assistant.

Learner Level: {learner_level}
Topic: {topic}

{material_section}
Create study material that contains EXACTLY these five sections, in this exact order:

1. Explanation
2. Short Summary
3. Important Points (exactly 5)
4. Practice Questions (exactly 5)
5. MCQs (exactly 5, each with a clear question, exactly four options A-D, and one correct answer)

Use this exact markdown template and do not add any other top-level sections:

## Explanation
Write a clear, accurate explanation suitable for the learner level.

## Short Summary
A concise summary of the topic in 3-5 sentences.

## Important Points
1. ...
2. ...
3. ...
4. ...
5. ...

## Practice Questions
1. ...
2. ...
3. ...
4. ...
5. ...

## MCQs
**Q1.** ...
A. ...
B. ...
C. ...
D. ...
Correct Answer: B

**Q2.** ...
A. ...
B. ...
C. ...
D. ...
Correct Answer: D

(continue the same format for Q3, Q4 and Q5)

{_build_accuracy_guidance(topic)}
{feedback_section}
At the very end, include the note: "Note: AI-generated study content may contain errors. Verify important information using trusted references."
"""


# ---------------------------------------------------------------------------
# Public generation API
# ---------------------------------------------------------------------------

def _build_feedback(validation: StudyValidationResult) -> str:
    """Build corrective feedback for the regeneration prompt.

    Blocking issues are always included.  Non-blocking overclaim warnings are
    added as suggestions so they are only ever surfaced when the output is
    already being regenerated.
    """
    if not validation:
        return ""
    lines = ["- " + issue for issue in validation.issues[:10]]
    if validation.warnings:
        lines.append("Non-blocking quality suggestions:")
        lines.extend("- " + warning for warning in validation.warnings[:5])
    return "\n".join(lines)


def generate_study_material(
    topic: str,
    learner_level: str = "Beginner",
    study_material: str = "",
    max_attempts: int = MAX_GENERATION_ATTEMPTS,
) -> StudyMaterialResult:
    """Generate validated five-section study material with bounded retries.

    Output is validated after every generation.  If a section is missing or an
    item count is wrong, the content is regenerated with corrective feedback,
    up to ``max_attempts`` times (bounded, never infinite).  Incomplete output
    is never returned as valid.
    """
    if not topic.strip():
        raise ValueError("Topic cannot be empty.")

    attempts = 0
    raw = ""
    cleaned = ""
    feedback = ""
    validation = None

    while attempts < max_attempts:
        attempts += 1
        prompt = _build_study_prompt(
            topic, learner_level, study_material, feedback
        )
        raw = (ask_llm(prompt) or "").strip()

        if not raw:
            feedback = (
                "The response was empty. Return the full five-section output "
                "using the exact template."
            )
            continue

        cleaned = repair_known_artifacts(raw)
        validation = validate_study_output(cleaned)

        if validation.is_valid:
            final_text = _append_verification_notice(cleaned)
            return StudyMaterialResult(
                status="valid",
                topic=topic,
                learner_level=learner_level,
                text=final_text,
                validation=validation,
                attempts=attempts,
            )

        feedback = _build_feedback(validation)

    if cleaned:
        final_text = _append_verification_notice(cleaned)
    else:
        final_text = _append_verification_notice(raw)
    issues = (
        validation.issues
        if validation and validation.issues
        else ["The LLM returned an empty response."]
    )
    return StudyMaterialResult(
        status="incomplete",
        topic=topic,
        learner_level=learner_level,
        text=final_text,
        validation=validation,
        attempts=attempts,
        message=f"Output was not fully valid after {attempts} attempt(s). "
                + "; ".join(issues),
    )


def generate_notes(
    topic: str,
    study_material: str = "",
    learner_level: str = "Beginner",
) -> str:
    """Backwards-compatible notes generator returning markdown text."""
    return generate_study_material(
        topic=topic,
        learner_level=learner_level,
        study_material=study_material,
    ).text


def _extract_verification_notice(lines) -> str:
    """Return the trailing verification notice block, if present.

    The notice is the user-facing sentence telling students that AI-generated
    content may contain errors.  It is rendered below a ``---`` separator.
    """
    notice_line = ""
    for line in reversed(lines):
        stripped = line.strip()
        if (
            "AI-generated study content" in stripped
            and stripped.lstrip().startswith("*")
        ):
            notice_line = stripped
            break
    if not notice_line:
        return ""
    return "\n\n---\n\n" + notice_line


def format_study_mcqs_for_display(text: str) -> str:
    """Reformat the MCQs section of generated notes for friendlier display.

    Each MCQ is rendered with its question, then each option on its own line,
    then the correct answer.  All other sections and the trailing verification
    notice are preserved exactly.
    """
    if not text or not isinstance(text, str):
        return text

    sections, positions, _ = extract_sections(text)
    mcqs = parse_mcqs(sections.get("MCQs") or "")
    if not mcqs or "MCQs" not in positions:
        return text

    lines = text.split("\n")
    heading_index = positions["MCQs"]

    prefix = "\n".join(lines[:heading_index]).rstrip()

    formatted = "## MCQs"
    for index, mcq in enumerate(mcqs, start=1):
        formatted += f"\n\n**MCQ {index}.** {mcq.question}"
        for letter in ("A", "B", "C", "D"):
            formatted += f"\n- {letter}. {mcq.options.get(letter, '')}"
        if mcq.correct_answer:
            formatted += f"\n- **Correct Answer:** {mcq.correct_answer}"

    return prefix + "\n\n" + formatted + _extract_verification_notice(lines)