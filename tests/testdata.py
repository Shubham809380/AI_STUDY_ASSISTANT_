"""Shared static test data used across the test suite."""

VALID_STUDY_TEXT = """## Explanation
Artificial Intelligence is a field of computer science that builds systems which
can perform tasks that normally require intelligence. Machine Learning is a
subset of AI that learns patterns from data rather than being a replacement for
human reasoning.

## Short Summary
AI is a broad field. ML is a subset of AI. AI systems are tools that
approximate tasks instead of thinking exactly like humans.

## Important Points
1. AI is a broad field of computer science.
2. Machine Learning is a subset of Artificial Intelligence.
3. AI systems are tools, not conscious entities.
4. AI includes NLP, computer vision and robotics.
5. AI models learn patterns from data.

## Practice Questions
1. What is the difference between AI and Machine Learning?
2. Name three sub-fields of AI.
3. Why should we avoid saying AI thinks exactly like a human?
4. What does supervised learning use?
5. Give one everyday example of AI.

## MCQs
**Q1.** Which statement best describes Machine Learning?
A. A complete replacement for human reasoning.
B. A subset of AI that learns patterns from data.
C. A programming language.
D. A type of computer hardware.
Correct Answer: B

**Q2.** Which sub-field generates human-like text?
A. Computer vision.
B. Robotics.
C. Natural Language Processing.
D. Database management.
Correct Answer: C

**Q3.** AI systems should be described as?
A. Conscious beings.
B. Tools that approximate tasks.
C. Humans in software.
D. Untrustworthy by definition.
Correct Answer: B

**Q4.** Which is a common AI application?
A. Spreadsheets only.
B. Editing binary code.
C. Speech recognition.
D. CPU cooling.
Correct Answer: C

**Q5.** Machine Learning mainly?
A. Learns patterns from data.
B. Rewrites web browsers.
C. Boosts battery life.
D. Compresses images.
Correct Answer: A
"""


INVALID_STUDY_TEXT = """## Explanation
X is a concept.

## Short Summary
A short summary.

## Important Points
1. A.
2. A.
3. B.
4. C.
5. D.

## Practice Questions
1. Q1?
2. Q2?

## MCQs
**Q1.** Which option?
A. one
B. two
C. three
Correct Answer: D

## MCQs
**Q2.** Extra?
A. one
B. two
C. three
D. four
Correct Answer: A
"""


def make_valid_quiz(count=5):
    return {
        "questions": [
            {
                "question": f"Question number {index}?",
                "options": {
                    "A": f"Option {index}A",
                    "B": f"Option {index}B",
                    "C": f"Option {index}C",
                    "D": f"Option {index}D",
                },
                "correct_answer": "B",
                "explanation": "Short explanation.",
            }
            for index in range(1, count + 1)
        ]
    }