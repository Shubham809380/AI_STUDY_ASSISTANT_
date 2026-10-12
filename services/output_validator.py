"""Validators and cleanup helpers for AI-generated study content.

The AI Study Assistant produces structured study material that must contain five
mandatory sections:

1. Explanation
2. Short Summary
3. Exactly 5 Important Points
4. Exactly 5 Practice Questions
5. Exactly 5 MCQs (question + exactly four options + one valid correct answer)

This module provides parsing and validation of that structure, per-MCQ
validation, duplicate detection and safe terminology / formatting cleanup.

Important design rule: invalid output is never silently marked as valid.
Every problem is reported through the ``issues`` list returned by the
validators.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Expected structure constants
# ---------------------------------------------------------------------------

SECTION_ORDER = [
    "Explanation",
    "Short Summary",
    "Important Points",
    "Practice Questions",
    "MCQs",
]

EXPECTED_IMPORTANT_POINTS = 5
EXPECTED_PRACTICE_QUESTIONS = 5
EXPECTED_MCQS = 5
EXPECTED_OPTIONS = 4
OPTION_KEYS = ("A", "B", "C", "D")

# Bounded regeneration guard.  Never loop forever.
MAX_GENERATION_ATTEMPTS = 3

VERIFICATION_NOTICE = (
    "\n\n---\n\n"
    "*Note: AI-generated study content may contain errors. "
    "Verify important information using trusted references such as "
    "textbooks, official documentation, and authoritative standards.*"
)

SECTION_ALIASES = {
    "Explanation": ["explanation", "explanation:"],
    "Short Summary": ["short summary", "short summary:", "summary"],
    "Important Points": ["important points", "key points", "important points:"],
    "Practice Questions": ["practice questions", "practice questions & answers"],
    "MCQs": ["mcqs", "mcq", "multiple choice questions",
             "multiple-choice questions", "mcqs (with correct answers)"],
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class MCQ:
    """A single multiple-choice question."""

    question: str = ""
    options: Dict[str, str] = field(default_factory=dict)
    correct_answer: str = ""
    explanation: str = ""


@dataclass
class StudyValidationResult:
    """Result of validating a five-section study output."""

    raw_text: str
    is_valid: bool = False
    explanation: str = ""
    summary: str = ""
    important_points: List[str] = field(default_factory=list)
    practice_questions: List[str] = field(default_factory=list)
    mcqs: List[MCQ] = field(default_factory=list)
    missing_sections: List[str] = field(default_factory=list)
    duplicate_headings: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_OPT_RE = re.compile(
    r"^\s*(?:[-*+•]\s*)?(?:\*\*)?(?:option\s*)?([A-Da-d])\s*[.).:\-/]\s*(.*)$"
)
_ANS_RE = re.compile(
    r"^\s*(?:\(?\s*)?(?:correct\s+)?answer\b\s*[:=.\-]?\s*([A-Da-d])\s*[.)]?\s*(.*)$",
    re.IGNORECASE,
)
_MARKER_RE = re.compile(r"^\s*Q?\s*\d+\s*[.)\-]?\s*(?P<rest>.*)$")
_ITEM_RE = re.compile(
    r"^\s*(?:[-*+•]|\((?:\d+|[A-D])\)|\d+\s*[.)]|[A-D]\s*[.)])\s+(.*)$"
)


def _normalize_heading(line: str) -> str:
    """Return a normalized, lowercase heading string for comparison."""
    text = line.strip()
    text = re.sub(r"^#{1,6}\s*", "", text)
    text = re.sub(r"^\s*[-*+•]\s*", "", text)
    text = re.sub(r"^\(?\d+[.)]?\)?\s*", "", text)
    text = re.sub(r"^\*\*|\*\*$", "", text)
    text = text.rstrip(":- .").strip()
    return re.sub(r"\s+", " ", text).lower().strip()


def _headings_map():
    return {section: SECTION_ALIASES[section] for section in SECTION_ORDER}


def _matches_section(text_norm: str, section: str) -> bool:
    for alias in SECTION_ALIASES[section]:
        if text_norm == alias or text_norm.startswith(alias + " "):
            return True
    return False


def _locate_headings(lines: List[str]):
    """Return (first_occurrence_position, occurrence_counts) per section."""
    positions: Dict[str, int] = {}
    counts: Dict[str, int] = {section: 0 for section in SECTION_ORDER}

    for index, line in enumerate(lines):
        norm = _normalize_heading(line)
        if not norm or len(norm) > 60:
            continue
        for section in SECTION_ORDER:
            if _matches_section(norm, section):
                counts[section] += 1
                if section not in positions:
                    positions[section] = index
                break
    return positions, counts


def extract_sections(raw_text: str):
    """Split raw markdown into the five canonical sections.

    Returns ``(sections, positions, counts)`` where ``sections`` maps a section
    name to its body text (or ``None`` when the heading was not found).
    """
    lines = raw_text.split("\n")
    positions, counts = _locate_headings(lines)

    sections: Dict[str, str] = {}
    for index, section in enumerate(SECTION_ORDER):
        start = positions.get(section)
        if start is None:
            sections[section] = None
            continue
        end = len(lines)
        for next_section in SECTION_ORDER[index + 1:]:
            next_pos = positions.get(next_section)
            if next_pos is not None and next_pos > start:
                end = next_pos
                break
        sections[section] = "\n".join(lines[start + 1:end]).strip()

    return sections, positions, counts


def parse_item_list(text: str) -> List[str]:
    """Extract bullet / numbered items from a section body."""
    if not text:
        return []
    items = []
    for line in text.split("\n"):
        match = _ITEM_RE.match(line)
        if match and match.group(1).strip():
            items.append(match.group(1).strip())
    return items


def _split_mcq_blocks(text: str) -> List[List[str]]:
    """Split an MCQs section into per-question blocks.

    A new block starts only when a question marker is seen (for example
    ``**Q1.**`` or ``1.``).  Option lines, answer lines, and explanations are
    appended to the current block, and stray leading text is ignored.
    """
    blocks: List[List[str]] = []
    current = None

    for raw_line in text.split("\n"):
        slim = raw_line.strip().replace("**", "").strip()
        if not slim:
            continue

        if _MARKER_RE.match(slim):
            if current is not None:
                blocks.append(current)
            current = [slim]
        elif current is not None:
            current.append(slim)

    if current is not None:
        blocks.append(current)
    return blocks


def _parse_mcq_block(lines: List[str]):
    """Parse one MCQ block; returns ``MCQ`` or ``None`` if not an MCQ block."""
    options: Dict[str, str] = {}
    answer = None
    question_lines: List[str] = []
    explanation_lines: List[str] = []

    for raw in lines:
        slim = raw.strip()
        opt = _OPT_RE.match(slim)
        if opt:
            letter = opt.group(1).upper()
            text = opt.group(2).strip()
            if letter in OPTION_KEYS:
                options[letter] = text
            continue

        ans = _ANS_RE.match(slim)
        if ans:
            answer = ans.group(1).upper()
            continue

        if re.match(r"(?i)^explanation\b", slim):
            explanation_lines.append(slim)
            continue

        marker = _MARKER_RE.match(slim)
        if marker:
            if answer is not None:
                continue
            rest = marker.group("rest").strip().strip(":").strip()
            if rest:
                question_lines.append(rest)
        elif answer is not None:
            continue
        else:
            question_lines.append(slim)

    if not options and answer is None:
        return None

    return MCQ(
        question=" ".join(question_lines) if question_lines else "",
        options=options,
        correct_answer=answer or "",
        explanation=" ".join(explanation_lines) if explanation_lines else "",
    )


def parse_mcqs(text: str) -> List[MCQ]:
    """Parse the MCQs section into ``MCQ`` objects."""
    if not text:
        return []
    mcqs: List[MCQ] = []
    for block in _split_mcq_blocks(text):
        mcq = _parse_mcq_block(block)
        if mcq is not None:
            mcqs.append(mcq)
    return mcqs


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_mcq(mcq, index: int = None) -> List[str]:
    """Validate a single MCQ (``MCQ`` instance or dict). Returns a list of issues."""
    prefix = f"MCQ {index}: " if index else "MCQ: "

    if isinstance(mcq, MCQ):
        question = mcq.question
        options = mcq.options
        answer = mcq.correct_answer
    elif isinstance(mcq, dict):
        question = mcq.get("question", "")
        options = mcq.get("options") or {}
        answer = mcq.get("correct_answer", "")
    else:
        return [prefix + "invalid format."]

    issues: List[str] = []

    if not question or not str(question).strip():
        issues.append(prefix + "missing question statement.")

    options_valid = isinstance(options, dict) and bool(options)
    if not options_valid:
        issues.append(
            prefix + "options must be exactly four options (A, B, C, D)."
        )
        options = {}

    present = {str(key).strip().upper() for key in (options.keys() if options_valid else [])}
    missing = sorted(set(OPTION_KEYS) - present)
    extra = sorted(present - set(OPTION_KEYS))
    if missing:
        issues.append(prefix + f"missing option(s): {', '.join(missing)}.")
    if extra:
        issues.append(prefix + f"unexpected option key(s): {', '.join(extra)}.")

    for key in OPTION_KEYS:
        current = options.get(key, "")
        if current is None or not str(current).strip():
            issues.append(prefix + f"option {key} is empty.")

    answer_norm = str(answer).strip().upper()
    if answer_norm not in OPTION_KEYS:
        issues.append(
            prefix + f"correct_answer '{answer}' must be one of A, B, C, or D."
        )
    elif not str(options.get(answer_norm, "")).strip():
        issues.append(
            prefix
            + f"correct answer '{answer_norm}' must correspond to an existing, "
            + "non-empty option."
        )

    return issues


def validate_mcqs(mcqs: List[MCQ]) -> List[str]:
    """Validate a list of MCQs and aggregate all issues."""
    issues: List[str] = []
    for index, mcq in enumerate(mcqs, start=1):
        issues.extend(validate_mcq(mcq, index))
    return issues


def validate_quiz_data(quiz_data, expected_count: int = None) -> List[str]:
    """Validate a quiz JSON object (as produced by the quiz generator)."""
    issues: List[str] = []

    if not isinstance(quiz_data, dict):
        return ["Quiz response is not a JSON object."]

    questions = quiz_data.get("questions")
    if not isinstance(questions, list):
        return ["Quiz response does not contain a 'questions' list."]

    if expected_count is not None and len(questions) != expected_count:
        issues.append(
            f"Quiz must contain exactly {expected_count} questions; got {len(questions)}."
        )

    for index, question in enumerate(questions, start=1):
        issues.extend(validate_mcq(question, index))

    return issues


def find_duplicate_items(items: List[str]) -> List[str]:
    """Return normalized descriptions of exact duplicate items."""
    normalized = []
    for item in items:
        key = re.sub(r"[^a-z0-9 ]", "", item.lower())
        key = re.sub(r"\s+", " ", key).strip()
        normalized.append(key)

    seen = set()
    duplicates = []
    for key in normalized:
        if not key:
            continue
        if key in seen and key not in duplicates:
            duplicates.append(key)
        seen.add(key)
    return duplicates


def check_numbering(text: str) -> List[str]:
    """Report issues when a numbered list is not sequential from 1."""
    if not text:
        return []
    numbers = [
        int(match.group(1))
        for line in text.split("\n")
        if (match := re.match(r"^\s*(\d+)\s*[.)]\s*", line))
    ]
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        return ["Numbered list is not sequential from 1."]
    return []


# ---------------------------------------------------------------------------
# Non-blocking overclaim warnings
# ---------------------------------------------------------------------------

# Lightweight patterns for unsupported universal claims.  These produce
# warnings only; they never block otherwise-valid output.
OVERCLAIM_PATTERNS = [
    (r"\balways\b", "'always'"),
    (r"\bnever\s+fails?\b", "'never fails'"),
    (r"\balways\s+fails?\b", "'always fails'"),
    (r"\btypically\s+consumes\s+the\s+majority\b", "'typically consumes the majority'"),
    (r"\bconsumes?\s+the\s+majority\b", "'consumes the majority'"),
    (r"\bai\s+thinks?\s+like\s+a\s+human\b", "'AI thinks like a human'"),
    (r"\bai\s+thinks?\s+like\s+humans?\b", "'AI thinks like a human'"),
    (r"\bai\s+understands?\b", "'AI understands'"),
    (r"\bai\s+is\s+conscious\b", "'AI is conscious'"),
]


def detect_overclaim_warnings(text: str) -> List[str]:
    """Detect non-blocking warnings for unsupported universal claims.

    Returns a list of human-readable warning strings.  These are advisory only
    and are kept separate from the blocking ``issues`` list.
    """
    warnings: List[str] = []
    if not text:
        return warnings
    for pattern, description in OVERCLAIM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            warnings.append(
                f"Possible unsupported claim detected: {description}."
            )
    return warnings


def validate_study_output(raw_text: str) -> StudyValidationResult:
    """Validate the five-section structure of generated study output.

    Never marks incomplete output as valid; all problems are returned through
    ``result.issues``.
    """
    raw = raw_text or ""
    sections, positions, counts = extract_sections(raw)

    issues: List[str] = []
    missing = [section for section in SECTION_ORDER if not sections.get(section)]
    if missing:
        issues.append(f"Missing required section(s): {', '.join(missing)}.")

    explanation = sections.get("Explanation") or ""
    summary = sections.get("Short Summary") or ""
    points_text = sections.get("Important Points") or ""
    practice_text = sections.get("Practice Questions") or ""
    mcqs_text = sections.get("MCQs") or ""

    if not explanation.strip():
        issues.append("Explanation section is empty.")
    if not summary.strip():
        issues.append("Short Summary section is empty.")

    important_points = parse_item_list(points_text)
    practice_questions = parse_item_list(practice_text)
    mcqs = parse_mcqs(mcqs_text)

    if len(important_points) != EXPECTED_IMPORTANT_POINTS:
        issues.append(
            f"Important Points must contain exactly {EXPECTED_IMPORTANT_POINTS} "
            f"items; got {len(important_points)}."
        )
    if len(practice_questions) != EXPECTED_PRACTICE_QUESTIONS:
        issues.append(
            f"Practice Questions must contain exactly {EXPECTED_PRACTICE_QUESTIONS} "
            f"items; got {len(practice_questions)}."
        )
    if len(mcqs) != EXPECTED_MCQS:
        issues.append(
            f"MCQs must contain exactly {EXPECTED_MCQS} questions; got {len(mcqs)}."
        )

    issues.extend(validate_mcqs(mcqs))

    duplicate_headings = [section for section, count in counts.items() if count > 1]
    if duplicate_headings:
        issues.append(
            "Duplicate section heading(s) found: "
            + ", ".join(duplicate_headings) + "."
        )

    duplicate_points = find_duplicate_items(important_points)
    if duplicate_points:
        issues.append(
            "Duplicate Important Points detected: " + ", ".join(duplicate_points) + "."
        )
    duplicate_practice = find_duplicate_items(practice_questions)
    if duplicate_practice:
        issues.append(
            "Duplicate Practice Questions detected: "
            + ", ".join(duplicate_practice) + "."
        )

    issues.extend(check_numbering(points_text))
    issues.extend(check_numbering(practice_text))

    return StudyValidationResult(
        raw_text=raw,
        is_valid=not issues,
        explanation=explanation,
        summary=summary,
        important_points=important_points,
        practice_questions=practice_questions,
        mcqs=mcqs,
        missing_sections=missing,
        duplicate_headings=duplicate_headings,
        issues=issues,
        warnings=detect_overclaim_warnings(raw),
    )


# ---------------------------------------------------------------------------
# Cleanup / terminology repair
# ---------------------------------------------------------------------------

_TERMINOLOGY_RULES = [
    # Acronym normalization first.  Every pattern is word-boundary-anchored so
    # normal words such as "again", "pain" or "brain" are never altered.
    (r"(?i)\ba\s*\.\s*i\s*\.", "AI"),
    (r"(?i)\bai\b", "AI"),
    (r"\b[Aa]rtificial [Ii]ntelligence\b", "Artificial Intelligence"),
    (r"\b[Aa]rtificial [Ii]ntellig[ei]n[ce]+\b", "Artificial Intelligence"),
    (r"\b[Ii]nfrastructure [Aa]s [Aa] [Ss]ervice\b", "Infrastructure as a Service"),
    (r"(?i)\biaas\b", "IaaS"),
    (r"(?i)\blaas\b", "IaaS"),
    (r"\b[Pp]latform [Aa]s [Aa] [Ss]ervice\b", "Platform as a Service"),
    (r"(?i)\bpaas\b", "PaaS"),
    (r"\b[Ss]oftware [Aa]s [Aa] [Ss]ervice\b", "Software as a Service"),
    (r"(?i)\bsaas\b", "SaaS"),
    (r"\b[Zz]ero [Tt]rust [Aa]rchitechture\b", "Zero Trust Architecture"),
    (r"\b[Zz]ero [Tt]rust [Aa]rchitecture\b", "Zero Trust Architecture"),
    (r"\b[Tt]ransport [Ll]ayer [Ss]ecurity\b", "Transport Layer Security"),
    (r"(?i)\btls\s*1\s*\.\s*3\b", "TLS 1.3"),
    (r"(?i)\btls1\.3\b", "TLS 1.3"),
    (r"(?i)\btls\b", "TLS"),
]


def clean_terminology(text: str) -> str:
    """Apply conservative terminology and spelling standardization."""
    if not text:
        return text
    output = text
    for pattern, replacement in _TERMINOLOGY_RULES:
        output = re.sub(pattern, replacement, output)
    return output


def remove_stray_artifacts(text: str) -> str:
    """Remove common formatting artifacts without touching real content."""
    if not text:
        return text

    output = re.sub(r"(?i)\bc\s*2\b", "", text)
    output = output.replace("\ufffd", "-")
    output = output.replace("\u00ad", "")
    output = re.sub(r"\s*```\s*", "", output)
    output = re.sub(r"^(#+)\s+#+", r"\1", output, flags=re.M)
    output = output.replace(":**:", ":**")
    output = re.sub(r"\n{4,}", "\n\n\n", output)
    return output.strip("\n")


def normalize_headings(text: str) -> str:
    """Normalize markdown heading markers while preserving heading text.

    Handles malformed headings such as ``## ## Explanation:`` and strips a
    trailing colon from the heading text.
    """
    if not text:
        return text
    lines = []
    for line in text.split("\n"):
        match = re.match(
            r"^(\s*)(#{1,6})(?:\s+#+)*\s+(.*?)\s*:?\s*$",
            line,
        )
        if match and match.group(3):
            level = len(match.group(2))
            lines.append(f"{'#' * level} {match.group(3).strip()}")
        else:
            lines.append(line)
    return "\n".join(lines)


def remove_duplicate_headings(text: str) -> str:
    """Remove repeated consecutive copies of the same section heading.

    Content under the duplicate heading is kept; only the duplicated heading
    line is dropped.  This is conservative and never drops passing content.
    """
    if not text:
        return text
    lines = text.split("\n")
    output = []
    last_section = None

    for line in lines:
        norm = _normalize_heading(line)
        current = None
        for section in SECTION_ORDER:
            if _matches_section(norm, section):
                current = section
                break
        if current is not None and current == last_section:
            continue
        output.append(line)
        if current is not None:
            last_section = current
    return "\n".join(output)


def repair_known_artifacts(text: str) -> str:
    """Apply all safe cleanup steps in a deterministic order."""
    output = remove_stray_artifacts(text or "")
    output = clean_terminology(output)
    output = remove_duplicate_headings(output)
    output = normalize_headings(output)
    return output.strip()