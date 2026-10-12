"""Runner for the five required topics (retest against the real Gemini API).

Usage:
    python scripts/retest_five_topics.py

This script generates validated five-section study material for the five
required topic / learner-level combinations, checks every output with the
validators, and prints a plain-text report.  It requires a working
``GEMINI_API_KEY`` in ``.env`` and sufficient API quota.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.notes_service import generate_study_material
from services.output_validator import validate_study_output

TOPICS = [
    ("Artificial Intelligence", "Beginner"),
    ("Cloud Computing", "Intermediate"),
    ("Data Analytics", "Intermediate"),
    ("Cybersecurity", "Advanced"),
    ("Web Development", "Beginner"),
]


def run():
    report = {"results": []}
    print("=" * 70)
    print("FIVE TOPIC RETEST (real Gemini calls)")
    print("=" * 70)

    for topic, level in TOPICS:
        entry = {"topic": topic, "learner_level": level}
        try:
            result = generate_study_material(topic, learner_level=level)
            entry["status"] = result.status
            entry["attempts"] = result.attempts
            entry["issues"] = list(result.validation.issues) if result.validation else []
            entry["message"] = result.message

            if result.validation is not None:
                validation = result.validation
                entry["stats"] = {
                    "important_points": len(validation.important_points),
                    "practice_questions": len(validation.practice_questions),
                    "mcqs": len(validation.mcqs),
                    "mcqs_complete": all(
                        (mcq.question.strip()
                         and set(mcq.options.keys()) == {"A", "B", "C", "D"}
                         and all(mcq.options[k].strip() for k in ("A", "B", "C", "D"))
                         and mcq.correct_answer in {"A", "B", "C", "D"})
                        for mcq in validation.mcqs
                    ),
                }
                entry["text_preview"] = result.text[:200]
        except Exception as error:  # noqa: BLE001 - report every failure
            entry["status"] = "error"
            entry["message"] = f"{type(error).__name__}: {error}"

        report["results"].append(entry)

        print(f"\n{topic} [{level}]")
        print(f"  status  : {entry['status']}")
        print(f"  attempts: {entry.get('attempts', 'n/a')}")
        print(f"  stats   : {entry.get('stats', {})}")
        if entry.get("issues"):
            for issue in entry["issues"]:
                print(f"  issue   : {issue}")
        if entry.get("message"):
            print(f"  message : {entry['message']}")
        if entry.get("text_preview"):
            print(f"  preview : {entry['text_preview'].splitlines()[0]}")

    print("\n" + "=" * 70)
    summary = {
        item["topic"]: item["status"]
        for item in report["results"]
    }
    print(json.dumps(summary, indent=2))

    out_path = ROOT / "test_output_five_topics.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nFull report written to: {out_path}")

    failed = [item for item in report["results"] if item["status"] != "valid"]
    if failed:
        print(f"\nRESULT: {len(failed)} of {len(TOPICS)} did not validate.")
        sys.exit(1)
    print(f"\nRESULT: all {len(TOPICS)} topics validated successfully.")
    sys.exit(0)


if __name__ == "__main__":
    run()