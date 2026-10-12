# AI Study Assistant - Testing Documentation

## 1. Testing Objective

The objective of testing is to verify that the major features of the AI-Powered Study Assistant work correctly and that user data is properly stored and retrieved through the SQL database.

## 1a. Automated Test Suite

A pytest suite was added to cover the validation and correction logic added in the improvement pass.

Run it from the project root:

```
python -m pytest tests -q
```

Result: **91 passed, 0 failed**

Coverage:

| Area | Files | What is verified |
| ---- | ----- | ---------------- |
| Structure validator | `tests/test_output_validator.py` | All 5 required sections detected; wrong item/MCQ counts flagged (4 and 6 of important points / practice questions / MCQs); missing section detected; duplicate headings and duplicate points flagged; inconsistent numbering detected |
| MCQ validator | `tests/test_output_validator.py` | Valid MCQ accepted; missing option D flagged (MCQ status must be `Incomplete`, never `Correct`); invalid correct answer flagged; empty question statement rejected; fewer than four options rejected; trailing text after an answer is ignored |
| Quiz-data validator | `tests/test_output_validator.py` | Valid JSON quiz accepted; wrong question count, invalid MCQ inside a quiz, and non-JSON input all rejected |
| Cleanup / terminology | `tests/test_output_validator.py` | `iaas/laas/paas/saas` capitalized to IaaS/PaaS/SaaS (both correct- and wrong-case spellings), `Tls 1.3` → TLS 1.3, `zero trust architecture` → Zero Trust Architecture, `A.I.`/`a.i.`/`Ai` → AI, malformed `## ##` headings normalized, stray `c2` artifact removed, repair is idempotent, words merely *containing* "ai" (again, pain, brain, fail) are untouched |
| Overclaim warnings | `tests/test_output_validator.py` | Non-blocking warnings are raised for overclaim phrases (`always`, `never fails`, `AI thinks like a human`, `AI understands`, `consumes the majority`) and reported in `StudyValidationResult.warnings`; clean output produces none; warnings never fail validation |
| Notes service | `tests/test_notes_service.py` | Five-section generation, bounded regeneration (never marks invalid output valid, exactly 2 LLM calls when the first attempt is invalid, stops after `MAX_GENERATION_ATTEMPTS` = 3), the five required topic/level combinations, `generate_notes` compatibility, verification notice appended exactly once (never duplicated) |
| Topic guidance | `tests/test_notes_service.py` | Data Analytics prompt covers all four analytics types plus the qualified preprocessing wording and the explicit "do not claim the majority" rule; Web Development prompt requires a real question statement and covers HTML/CSS/JavaScript roles; matching is case-insensitive; Machine Learning falls back to AI guidance |
| MCQ display formatting | `tests/test_notes_service.py` | `format_study_mcqs_for_display` renders each option on its own line (`- A.` – `- D.`), keeps the question text and `Correct Answer` lines, preserves the other four sections, and keeps the verification notice exactly once |
| Quiz service | `tests/test_quiz_service.py` | Valid quizzes returned; invalid/Malformed JSON regenerates until valid; retries are bounded and raise `ValueError`; wrong question count regenerates |
| Database layer | `tests/test_database.py` | Initialization, subjects, notes, quizzes, quiz questions, result storage, study sessions (uses a temporary SQLite file) |

## 2. Functional Test Cases

| Test ID | Feature             | Test Input / Action                      | Expected Result                                  | Actual Result                                      | Status |
| ------- | ------------------- | ---------------------------------------- | ------------------------------------------------ | -------------------------------------------------- | ------ |
| TC-01   | Dashboard           | Open application                         | Dashboard loads without error                    | Dashboard loaded successfully                      | PASS   |
| TC-02   | Ask AI              | Ask: "What is inheritance in Python?"    | AI response is generated                         | Feature worked; API quota may limit later requests | PASS   |
| TC-03   | Notes Generator     | Topic: Python Functions                  | AI-generated notes are displayed                 | Notes generated successfully                       | PASS   |
| TC-04   | Quiz Generator      | Topic: Python Functions, 5 questions     | Quiz questions are generated                     | Quiz generated successfully                        | PASS   |
| TC-05   | Quiz Evaluation     | Submit generated quiz                    | Score and percentage are displayed               | Score displayed successfully                       | PASS   |
| TC-06   | Quiz Result Storage | Submit quiz                              | Result is saved in SQL database                  | Result saved successfully                          | PASS   |
| TC-07   | Progress            | Open Progress page after quiz            | Attempts, average score and best score displayed | Data displayed successfully                        | PASS   |
| TC-08   | Study Session       | Save Python study session for 30 minutes | Session is stored in SQL                         | Session saved successfully                         | PASS   |
| TC-09   | Study History       | Open Study History                       | Saved session is displayed                       | Session displayed successfully                     | PASS   |
| TC-10   | Jupyter + SQL       | Load quiz results into Pandas            | SQL data appears in notebook                     | Data loaded successfully                           | PASS   |

## 3. Database Testing

The following database operations were tested:

* Database initialization
* User retrieval
* Subject retrieval
* Notes storage
* Quiz storage
* Quiz question storage
* Quiz result storage
* Study session storage
* Study history retrieval

## 4. LLM/API Testing

LLM integration was successfully connected and tested through the Python service layer and Streamlit application.

The model used is `gemini-flash-lite-latest` by default (overridable via the `GEMINI_MODEL` environment variable, configured in `services/llm_service.py`).

During repeated experimentation, the Gemini API free-tier request quota was reached.

Example error:

`429 RateLimitError - quota exceeded`

This is an external API usage limitation and does not indicate a database or Streamlit logic failure.

### 4a. Structured Output Retest (6th-Area Improvement Verification)

The five required topics were regenerated against the live Gemini API using the new validator with bounded regeneration. Every topic passed the 5-section structural validator on the **first attempt**:

| Topic | Learner Level | Status | Attempts | Important Points | Practice Questions | MCQs (complete) |
| ----- | ------------- | ------ | ------- | ---------------- | ------------------ | --------------- |
| Artificial Intelligence | Beginner | PASS | 1 | 5 | 5 | 5 |
| Cloud Computing | Intermediate | PASS | 1 | 5 | 5 | 5 |
| Data Analytics | Intermediate | PASS | 1 | 5 | 5 | 5 |
| Cybersecurity | Advanced | PASS | 1 | 5 | 5 | 5 |
| Web Development | Beginner | PASS | 1 | 5 | 5 | 5 |

Full machine-readable report: `test_output_five_topics.json`.

Sample integrity checks performed on the live output:

* Terminology: `IaaS/PaaS/SaaS` correctly capitalized; no stray `c2` artifacts; `AI` used per standard convention.
* Cybersecurity (Advanced): NIST SP 800-207 PDP / Policy Engine / Policy Administrator / PEP distinctions are accurate; TLS 1.3 forward secrecy is correctly qualified (ephemeral full handshakes provide it; PSK-only and 0-RTT early-data do not); no single control is claimed to "secure" a system.
* Educational verification notice appears exactly once per generated note.

The retest was repeated in the final improvement pass; all five topics again passed on the first attempt (1 generation each, no regeneration needed). The regenerated machine-readable report in `test_output_five_topics.json` contains no secrets.

## 5. Jupyter Notebook Testing

The Jupyter Notebook was successfully connected to the project `.venv` environment.

Verified operations:

* Python environment check
* Pandas import
* SQL data retrieval
* SQL data conversion to Pandas DataFrame
* Quiz performance calculation
* LLM experimentation setup

## 6. Testing Result

The core application features were tested successfully.

Overall test status:

**PASS**

The application is ready for the next phase of documentation, demonstration and final submission preparation.
