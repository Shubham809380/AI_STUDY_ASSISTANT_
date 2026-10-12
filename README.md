# AI Study Assistant

## 1. Project Overview

AI Study Assistant is an AI-powered learning application designed to help students study, generate learning content, attempt quizzes, and track their study progress.

The application combines Python, Streamlit, SQLite, Jupyter Notebook, and a Gemini-based LLM service.

## 2. Main Features

* AI-powered question answering
* AI-generated study notes
* AI-generated multiple-choice quizzes
* Structured output validation (five mandatory sections, exactly 5 important points, 5 practice questions and 5 MCQs)
* Bounded regeneration with corrective feedback (invalid output is never silently accepted)
* Safe terminology / formatting cleanup (headings, spelling, stray artifacts)
* Non-blocking quality suggestions (overclaim / overgeneralization warnings)
* MCQ display formatting (each option on its own line)
* Friendly API error handling (quota, auth and network errors)
* Quiz scoring and result storage
* Progress tracking
* Study session tracking
* Study streak tracking (consecutive calendar days)
* Add subjects directly from the Study Session page
* Study history with subject-based filtering and deletion
* SQL-based data storage
* Automated pytest test suite
* Jupyter Notebook based data analysis and LLM experimentation

## 3. Technologies Used

* Python
* Streamlit
* SQLite
* Google Gemini API (`google-genai`)
* Pandas
* Matplotlib
* Jupyter Notebook
* ipykernel
* python-dotenv
* pytest

## 4. Project Structure

```text
AI_STUDY_ASSISTANT_SUBMISSION/
│
├── database/
│   ├── database.py
│   └── schema.sql
│
├── services/
│   ├── llm_service.py
│   ├── notes_service.py
│   ├── quiz_service.py
│   ├── output_validator.py
│   └── display_utils.py
│
├── scripts/
│   └── retest_five_topics.py
│
├── tests/
│   ├── conftest.py
│   ├── testdata.py
│   ├── test_database.py
│   ├── test_notes_service.py
│   ├── test_output_validator.py
│   ├── test_quiz_service.py
│   ├── test_study_sessions.py
│   └── test_subjects.py
│
├── notebooks/
│   └── 01_llm_experiments.ipynb
│
├── app.py
├── requirements.txt
├── README.md
├── TESTING.md
├── test_output_five_topics.json
├── .gitignore
└── .env.example
```

`services/output_validator.py` holds the structure validators, per-MCQ validation,
duplicate detection and safe terminology / formatting cleanup used by the notes
and quiz services.

`services/display_utils.py` holds the small pure helpers used by the Streamlit UI
(study-session and subject validation, topic trimming, subject capitalization,
timestamp formatting and subject filtering) so they run unit-testable without
Streamlit.

Study sessions support validation, a current study streak (consecutive calendar
days ending today or yesterday) and a deletable, filterable history.  Subjects
can be added directly from the Study Session page.

### Study Session & Progress

* **Add subject** — a subject can be added straight from the Study Session page.
  The form validates that the name is non-empty, at most 50 characters and not a
  duplicate (case-insensitive). When the user has no subjects yet, the form is
  shown inline; otherwise it lives in a collapsed `➕ Add new subject` expander.
* **Save session** — the topic must be non-empty (trimmed and capped at 100
  characters) and the duration must be 1–600 minutes. After a successful save the
  topic input is cleared and a success message is shown.
* **Study streak** — counts consecutive calendar days with at least one session,
  ending today (or yesterday). Same-day sessions count once; no sessions = 0.
* **Study history** — sessions are listed newest-first with the topic capitalized
  for display (stored unchanged) and a readable timestamp. History can be filtered
  by subject (with matching totals) and individual sessions can be deleted after
  confirmation.

## 5. Installation

Create and activate a Python virtual environment.

Then install the required packages:

```bash
python -m pip install -r requirements.txt
```

## 6. API Key Setup

The submitted project does not contain a private API key.

To use the AI features locally:

1. Copy `.env.example` and rename the copy to `.env`.
2. Open the new `.env` file.
3. Add your own Gemini API key:

```text
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

4. Keep the `.env` file local and do not submit it.

The `.env.example` file is only a configuration template and does not contain a real API key.

## 7. Running the Application

After installing the dependencies and configuring the local `.env` file, run:

```bash
python -m streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## 8. Database

The application uses SQLite for persistent data storage.

The database is initialized automatically when the application starts.

The database schema is defined in:

```text
database/schema.sql
```

The local SQLite database file is generated during runtime and is not included in the submitted project.

## 9. Jupyter Notebook

The project includes a Jupyter Notebook for:

* SQL data analysis
* Pandas-based analysis
* Quiz performance analysis
* LLM experiments
* Prompt comparison

Open:

```text
notebooks/01_llm_experiments.ipynb
```

and select the project virtual-environment Python kernel.

## 9a. Structured Output Validation and Regeneration

Generated study content must follow five mandatory sections, in order:

1. Explanation
2. Short Summary
3. Important Points (exactly 5)
4. Practice Questions (exactly 5)
5. MCQs (exactly 5, each with a clear question, four options A-D and one valid correct answer)

`services/output_validator.py` validates this structure: missing or duplicate
sections, wrong item / MCQ counts, invalid options and incorrect answers are all
reported as issues. Invalid output is never silently accepted.

Both the notes service and quiz service use a bounded regeneration loop
(`MAX_GENERATION_ATTEMPTS = 3`): when validation fails, the model is asked again
with corrective feedback. Notes that still fail are returned with status
`incomplete`; quizzes that still fail raise a clear `ValueError`.

A safe cleanup pass (`repair_known_artifacts`) is applied before validation,
covering malformed headings (`## ## Heading`), stray artifacts (e.g. `c2`),
terminology capitalization (IaaS/PaaS/SaaS, TLS 1.3, Zero Trust Architecture),
and a verification notice that is appended exactly once.

### Accuracy guidance

`notes_service.py` also embeds topic-specific accuracy guidance so generated
content avoids unsupported universal claims. Examples:

* AI: machine learning is a subset of AI; never claims systems "think" like humans.
* Cloud: IaaS/PaaS/SaaS and shared-responsibility model described precisely.
* Cybersecurity: NIST SP 800-207 PDP / Policy Engine / Policy Administrator / PEP distinctions; TLS 1.3 forward secrecy correctly qualified.

The model is configured in `services/llm_service.py` (default
`gemini-flash-lite-latest`, overridable via `GEMINI_MODEL`), with a 60-second
request timeout and friendly messages for quota (429), auth (401/403) and
network errors.

## 10. Testing

An automated pytest suite is included in:

```text
tests/
```

Run it from the project root:

```bash
python -m pytest tests -q
```

Result: **147 passed, 0 failed**.

Coverage includes the structure / MCQ / quiz-data validators, terminology and
artifact cleanup, overclaim warnings, notes and quiz generation and regeneration
behaviour, MCQ display formatting, the database layer, study-session validation
and streak logic, study-history display helpers (timestamp formatting, topic
capitalization, subject filtering, deletion) and add-subject behaviour.

The five required topic/level combinations were also regenerated against the
live Gemini API (`scripts/retest_five_topics.py`); all five passed validation on
the first attempt (1 attempt each). The machine-readable report is in
`test_output_five_topics.json`.

Additional manual testing documentation is available in:

```text
TESTING.md
```

The application has been tested for dashboard access, AI interaction, note generation, quiz generation, quiz evaluation, progress tracking, study sessions, study history, and Jupyter/SQL integration.

## 11. API Key Security

Private API keys must not be included in submitted project files.

The actual `.env` file must remain local and must not be uploaded or submitted.

The `.env.example` file is provided only as a safe configuration template.

## 12. Important Note

AI-generated information should be verified before being used as factual or academic content.

## 13. Submission Contents

The submission package (`AI_STUDY_ASSISTANT_SUBMISSION.zip`) contains a single
top-level folder named `AI_STUDY_ASSISTANT_SUBMISSION/` with:

* `app.py` — the Streamlit application
* `database/` — `database.py` and `schema.sql`
* `services/` — `llm_service.py`, `notes_service.py`, `quiz_service.py`,
  `output_validator.py`, `display_utils.py`
* `scripts/` — `retest_five_topics.py`
* `tests/` — the full pytest suite (`test_*.py`, `conftest.py`, `testdata.py`)
* `notebooks/` — `01_llm_experiments.ipynb`
* `README.md`, `TESTING.md`, `requirements.txt`, `.gitignore`, `.env.example`
* `test_output_five_topics.json` — machine-readable retest report

The following are NOT included in the submission:

* `.env`
* Private API keys
* `.venv`
* `venv`
* `__pycache__`
* `.pytest_cache`
* `.git`
* Local SQLite database files (`*.db`)
