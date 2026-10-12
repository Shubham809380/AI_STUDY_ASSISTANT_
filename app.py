import streamlit as st

from database.database import (
    initialize_database,
    get_subjects,
    create_quiz,
    save_quiz_question,
    save_quiz_result,
    get_quiz_results,
    get_total_notes,
    get_total_quizzes,
    get_average_score,
    get_total_study_sessions,
    get_total_study_minutes,
    add_study_session,
    get_study_sessions
)
from services.llm_service import ask_llm


# Initialize database
initialize_database()


# Page configuration
st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="🤖",
    layout="wide"
)

# ============================================================
# PREMIUM UI STYLING
# ============================================================

st.markdown(
    """
    <style>

    /* Main application background */
    .stApp {
        background:
            radial-gradient(
                circle at 10% 10%,
                rgba(80, 90, 255, 0.16),
                transparent 28%
            ),
            radial-gradient(
                circle at 90% 20%,
                rgba(0, 210, 255, 0.12),
                transparent 25%
            ),
            radial-gradient(
                circle at 50% 90%,
                rgba(140, 60, 255, 0.10),
                transparent 30%
            ),
            linear-gradient(
                135deg,
                #070b14 0%,
                #0b1020 45%,
                #080c16 100%
            );

        background-attachment: fixed;
    }

    /* Subtle AI grid */
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;

        background-image:
            linear-gradient(
                rgba(255,255,255,0.025) 1px,
                transparent 1px
            ),
            linear-gradient(
                90deg,
                rgba(255,255,255,0.025) 1px,
                transparent 1px
            );

        background-size: 42px 42px;
        pointer-events: none;
        z-index: 0;
    }

    /* Main content */
    .block-container {
        position: relative;
        z-index: 1;
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                rgba(9, 13, 25, 0.97),
                rgba(13, 18, 32, 0.97)
            );

        border-right: 1px solid rgba(255,255,255,0.08);
    }

    /* Sidebar title */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #f8fafc;
    }

    /* Sidebar navigation */
    section[data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 12px;
        padding: 8px 10px;
        transition: 0.2s ease;
    }

    section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.06);
    }

    /* Main title */
    h1 {
        letter-spacing: -0.5px;
        font-weight: 800;
    }

    h2, h3 {
        font-weight: 750;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background:
            linear-gradient(
                145deg,
                rgba(255,255,255,0.075),
                rgba(255,255,255,0.025)
            );

        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 18px;
        padding: 18px 20px;
        backdrop-filter: blur(14px);
        box-shadow:
            0 8px 30px rgba(0,0,0,0.25),
            inset 0 1px 0 rgba(255,255,255,0.04);

        min-height: 125px;
    }

    div[data-testid="stMetric"]:hover {
        border-color: rgba(120,150,255,0.35);
        transform: translateY(-2px);
        transition: 0.2s ease;
    }

    div[data-testid="stMetricLabel"] {
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        font-weight: 800;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.10);
        background:
            linear-gradient(
                135deg,
                rgba(90,105,255,0.95),
                rgba(120,70,220,0.95)
            );
        color: white;
        font-weight: 700;
        box-shadow:
            0 8px 22px rgba(70,70,180,0.25);
        transition: 0.2s ease;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow:
            0 12px 28px rgba(70,70,180,0.35);
    }

    /* Text inputs */
    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="select"] {
        border-radius: 12px;
    }

    /* Info / success / warning boxes */
    div[data-testid="stAlert"] {
        border-radius: 14px;
    }

    /* Subject cards */
    .subject-card {
        background:
            linear-gradient(
                135deg,
                rgba(35,75,120,0.45),
                rgba(25,40,75,0.30)
            );

        border: 1px solid rgba(100,160,255,0.14);
        border-radius: 14px;

        padding: 14px 18px;
        margin-bottom: 10px;

        backdrop-filter: blur(10px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.18);

        font-weight: 600;
    }

    /* Hero */
    .hero-card {
        position: relative;
        overflow: hidden;

        background:
            linear-gradient(
                135deg,
                rgba(55,70,170,0.34),
                rgba(80,40,150,0.20)
            );

        border: 1px solid rgba(140,150,255,0.15);
        border-radius: 24px;

        padding: 30px 34px;
        margin-bottom: 28px;

        backdrop-filter: blur(18px);
        box-shadow:
            0 18px 50px rgba(0,0,0,0.30);
    }

    .hero-card::after {
        content: "";
        position: absolute;

        width: 180px;
        height: 180px;

        right: -50px;
        top: -50px;

        background: radial-gradient(
            circle,
            rgba(90,160,255,0.25),
            transparent 70%
        );

        border-radius: 50%;
    }

    .hero-kicker {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        opacity: 0.7;
        margin-bottom: 8px;
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .hero-subtitle {
        font-size: 1rem;
        opacity: 0.78;
    }
    /* Premium sidebar branding */
.sidebar-brand {
    padding: 10px 4px 20px 4px;
    text-align: center;
}

.sidebar-icon {
    font-size: 2.6rem;
    margin-bottom: 6px;
}

.sidebar-name {
    font-size: 1.15rem;
    font-weight: 800;
    letter-spacing: 1.8px;
    color: #f8fafc;
}

.sidebar-subtitle {
    margin-top: 4px;
    font-size: 0.62rem;
    letter-spacing: 2.2px;
    color: rgba(255,255,255,0.52);
}
/* Premium navigation */
section[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 6px;
}

section[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 10px 12px;
    border-radius: 12px;
    margin: 3px 0;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}

section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(100, 120, 255, 0.10);
    border-color: rgba(120, 140, 255, 0.15);
}

section[data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
    background:
        linear-gradient(
            135deg,
            rgba(75, 95, 210, 0.28),
            rgba(120, 70, 200, 0.20)
        );
    border-color: rgba(130, 150, 255, 0.28);
    box-shadow:
        0 6px 20px rgba(50, 60, 140, 0.18);
}
/* Quick action cards */

.action-card {
    background:
        linear-gradient(
            145deg,
            rgba(255,255,255,0.065),
            rgba(255,255,255,0.025)
        );

    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;

    padding: 22px;
    min-height: 145px;

    backdrop-filter: blur(14px);

    box-shadow:
        0 10px 30px rgba(0,0,0,0.22);

    transition: all 0.2s ease;
}

.action-card:hover {
    transform: translateY(-4px);
    border-color: rgba(120,140,255,0.28);
    box-shadow:
        0 14px 34px rgba(50,60,140,0.18);
}

.action-icon {
    font-size: 1.7rem;
    margin-bottom: 10px;
}

.action-title {
    font-size: 1.05rem;
    font-weight: 750;
    margin-bottom: 5px;
}

.action-text {
    font-size: 0.82rem;
    opacity: 0.68;
    line-height: 1.5;
}

/* Progress cards */
div[data-testid="stProgress"] > div {
    border-radius: 10px;
}

div[data-testid="stProgress"] > div > div {
    border-radius: 10px;
}

/* Study session form */
div[data-testid="stForm"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 20px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px;
}






    </style>
    """,
    unsafe_allow_html=True
)
# Temporary demo user
USER_ID = 1


# Sidebar
st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="sidebar-icon">🤖</div>
        <div class="sidebar-name">AI STUDY</div>
        <div class="sidebar-subtitle">SMART LEARNING LAB</div>
    </div>
    """,
    unsafe_allow_html=True
)

pages = [
    "🏠 Dashboard",
    "💬 Ask AI",
    "📝 Generate Notes",
    "❓ Generate Quiz",
    "📊 Progress",
    "⏱️ Study Session",
    "🕒 Study History"
]

default_page = st.session_state.pop("quick_page", "🏠 Dashboard")

page = st.sidebar.radio(
    "Navigation",
    pages,
    index=pages.index(default_page)
)

# ============================================================
# DASHBOARD
# ============================================================

if page == "🏠 Dashboard":

    st.title("🤖 AI-Powered Study Assistant")

    # Premium Hero
    st.markdown(
        """
<div class="hero-card">
    <div class="hero-kicker">AI LEARNING WORKSPACE</div>
    <div class="hero-title">Learn smarter. Track better.</div>
    <div class="hero-subtitle">
        Your intelligent study companion for learning, practice and progress.
    </div>
</div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("📊 Dashboard")

    subjects = get_subjects(USER_ID)

    # SQL statistics
    total_notes = get_total_notes(USER_ID)
    total_quizzes = get_total_quizzes(USER_ID)
    average_score = get_average_score(USER_ID)
    total_sessions = get_total_study_sessions(USER_ID)
    total_minutes = get_total_study_minutes(USER_ID)

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📚 Subjects",
            value=len(subjects)
        )

    with col2:
        st.metric(
            label="📝 Notes",
            value=total_notes
        )

    with col3:
        st.metric(
            label="❓ Quizzes",
            value=total_quizzes
        )

    with col4:
        st.metric(
            label="🎯 Average Score",
            value=f"{average_score:.1f}%"
        )

    # Study Statistics
    st.subheader("📈 Study Statistics")

    if average_score >= 80:
        performance = "Excellent 🌟"
    elif average_score >= 60:
        performance = "Good 👍"
    elif average_score > 0:
        performance = "Needs Improvement 📖"
    else:
        performance = "No quiz data yet"

    stats_col1, stats_col2, stats_col3 = st.columns(3)

    with stats_col1:
        st.metric(
            label="⏱️ Study Sessions",
            value=total_sessions
        )

    with stats_col2:
        st.metric(
            label="⌛ Study Time",
            value=f"{total_minutes} min"
        )

    with stats_col3:
        st.metric(
            label="📊 Performance",
            value=performance
        )

    # My Subjects
    st.subheader("📚 My Subjects")

    if subjects:

        for subject in subjects:

            st.markdown(
                f"""
<div class="subject-card">
    📘 {subject['subject_name']}
</div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.warning(
            "No subjects found."
        )

# ============================================================
# STUDY OVERVIEW
# ============================================================

    st.subheader("🧠 Study Overview")

    overview_col1, overview_col2 = st.columns(2)

    with overview_col1:
        st.markdown("#### 🎯 Quiz Performance")
        st.progress(min(average_score / 100, 1.0))
        st.caption(f"Current average score: {average_score:.1f}%")

    with overview_col2:
        st.markdown("#### ⏱️ Study Time")
        study_hours = total_minutes / 60
        st.metric(
            label="Total Learning Time",
            value=f"{study_hours:.1f} hrs"
        )
        st.caption(f"{total_minutes} minutes recorded")

    # ============================================================
    # QUICK ACTIONS
    # ============================================================

    st.subheader("⚡ Quick Actions")

    action_col1, action_col2, action_col3 = st.columns(3)

    with action_col1:
        if st.button("🤖 Ask AI", use_container_width=True):
            st.session_state["quick_page"] = "💬 Ask AI"
            st.rerun()

    with action_col2:
        if st.button("📝 Generate Notes", use_container_width=True):
            st.session_state["quick_page"] = "📝 Generate Notes"
            st.rerun()

    with action_col3:
        if st.button("❓ Generate Quiz", use_container_width=True):
            st.session_state["quick_page"] = "❓ Generate Quiz"
            st.rerun()

# ============================================================
# ASK AI
# ============================================================

elif page == "💬 Ask AI":

    st.title("💬 Ask AI")

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">AI STUDY ASSISTANT</div>
            <div class="hero-title">Ask. Learn. Understand.</div>
            <div class="hero-subtitle">
                Get clear, student-friendly explanations for your study questions.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("🧠 Your Question")

    question = st.text_area(
        "Enter your question:",
        placeholder=(
            "Example: Explain inheritance in Python "
            "with a simple example."
        ),
        height=180
    )

    st.markdown("")

    if st.button(
        "✨ Ask AI",
        type="primary",
        use_container_width=True
    ):

        if not question.strip():

            st.warning(
                "Please enter a question first."
            )

        else:

            with st.spinner("🤖 Thinking..."):

                try:

                    prompt = f"""
You are an AI study assistant.

Answer the student's question clearly and accurately.

Student Question:
{question}

Requirements:
- Use simple language.
- Explain the concept clearly.
- Give examples when useful.
- Focus on educational value.
- Avoid unnecessary information.
"""

                    answer = ask_llm(prompt)

                    st.success(
                        "AI response generated successfully!"
                    )

                    st.subheader("🤖 AI Response")

                    with st.container(border=True):

                        st.markdown(answer)

                except Exception as error:

                    st.error(
                        f"Unable to generate response: {error}"
                    )



                    
# ============================================================
# GENERATE NOTES
# ============================================================

elif page == "📝 Generate Notes":

    st.title("📝 AI Notes Generator")

    st.markdown(
        """
        ### 🧠 Learn faster with structured notes
        Enter a topic or paste your study material and let AI organize it for you.
        """
    )

    st.divider()

    notes_col1, notes_col2 = st.columns([1, 1])

    with notes_col1:
        topic = st.text_input(
            "📚 Topic",
            placeholder="Example: Python Functions"
        )

    with notes_col2:
        subjects = get_subjects(USER_ID)

        subject_options = {
            subject["subject_name"]: subject["subject_id"]
            for subject in subjects
        }

        selected_subject = None

        if subject_options:
            selected_subject = st.selectbox(
                "📘 Subject",
                list(subject_options.keys())
            )

        learner_level = st.selectbox(
            "🎓 Learner Level",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ]
        )

    study_material = st.text_area(
        "📖 Study Material (optional)",
        placeholder=(
            "Paste textbook content, class notes, "
            "or any study material here..."
        ),
        height=220
    )

    generate_button = st.button(
        "✨ Generate Notes",
        type="primary",
        use_container_width=True
    )

    if generate_button:

        if not topic.strip():

            st.warning(
                "Please enter a topic first."
            )

        else:

            with st.spinner("🧠 Generating structured notes..."):

                try:

                    from services.notes_service import (
                        format_study_mcqs_for_display,
                        generate_study_material,
                    )
                    from database.database import save_note

                    result = generate_study_material(
                        topic=topic,
                        learner_level=learner_level,
                        study_material=study_material
                    )

                    generated_notes = result.text

                    if result.status == "valid":

                        st.success(
                            f"Notes generated successfully! "
                            f"({result.attempts} attempt(s))"
                        )

                    else:

                        st.warning(
                            "Generated output is incomplete and will be "
                            "displayed for reference. "
                            "The following issues were detected: "
                            f"{result.message}"
                        )

                    st.subheader("📚 Generated Notes")
                    st.markdown(
                        format_study_mcqs_for_display(generated_notes)
                    )
                    st.divider()

                    subject_id = (
                        subject_options[selected_subject]
                        if selected_subject
                        else None
                    )

                    if st.button(
                        "💾 Save Notes",
                        use_container_width=True
                    ):

                        note_id = save_note(
                            user_id=USER_ID,
                            subject_id=subject_id,
                            title=topic,
                            source_text=study_material,
                            generated_notes=generated_notes
                        )

                        st.success(
                            f"Notes saved successfully! Note ID: {note_id}"
                        )

                except Exception as error:

                    st.error(
                        f"Unable to generate notes: {error}"
                    )

# ============================================================
# GENERATE QUIZ
# ============================================================

elif page == "❓ Generate Quiz":

    st.title("❓ AI Quiz Generator")

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">SMART PRACTICE LAB</div>
            <div class="hero-title">Test your knowledge.</div>
            <div class="hero-subtitle">
                Generate personalized multiple-choice quizzes and measure your understanding.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("⚙️ Quiz Setup")

    subjects = get_subjects(USER_ID)

    subject_options = {
        subject["subject_name"]: subject["subject_id"]
        for subject in subjects
    }

    quiz_col1, quiz_col2 = st.columns(2)

    with quiz_col1:

        topic = st.text_input(
            "📚 Quiz Topic",
            placeholder="Example: Python Object-Oriented Programming"
        )

        number_of_questions = st.number_input(
            "📝 Number of Questions",
            min_value=1,
            max_value=20,
            value=5,
            step=1
        )

    with quiz_col2:

        difficulty = st.selectbox(
            "🎯 Difficulty",
            [
                "Easy",
                "Medium",
                "Hard"
            ]
        )

        selected_subject = None

        if subject_options:

            selected_subject = st.selectbox(
                "📘 Subject",
                list(subject_options.keys())
            )

    st.markdown("")

    if st.button(
        "✨ Generate Quiz",
        type="primary",
        use_container_width=True
    ):

        if not topic.strip():

            st.warning(
                "Please enter a quiz topic first."
            )

        else:

            try:

                from services.quiz_service import generate_quiz

                with st.spinner(
                    "🧠 Generating your quiz..."
                ):

                    quiz = generate_quiz(
                        topic=topic,
                        number_of_questions=number_of_questions,
                        difficulty=difficulty
                    )

                quiz_id = create_quiz(
                    user_id=USER_ID,
                    subject_id=(
                        subject_options[selected_subject]
                        if selected_subject
                        else None
                    ),
                    topic=topic,
                    difficulty=difficulty,
                    total_questions=len(
                        quiz["questions"]
                    )
                )

                for question in quiz["questions"]:

                    options = question["options"]

                    save_quiz_question(
                        quiz_id=quiz_id,
                        question_text=question["question"],
                        option_a=options["A"],
                        option_b=options["B"],
                        option_c=options["C"],
                        option_d=options["D"],
                        correct_answer=question["correct_answer"],
                        explanation=question.get(
                            "explanation",
                            ""
                        )
                    )

                st.session_state["generated_quiz"] = quiz
                st.session_state["quiz_id"] = quiz_id
                st.session_state["quiz_topic"] = topic
                st.session_state["quiz_difficulty"] = difficulty
                st.session_state["quiz_subject_id"] = (
                    subject_options[selected_subject]
                    if selected_subject
                    else None
                )

                st.success(
                    "Quiz generated successfully!"
                )

            except Exception as error:

                st.error(
                    f"Unable to generate quiz: {error}"
                )

# ============================================================
# DISPLAY GENERATED QUIZ
# ============================================================

if (
    "generated_quiz" in st.session_state
    and page == "❓ Generate Quiz"
):

    quiz = st.session_state["generated_quiz"]

    st.divider()
    st.subheader("📝 Quiz")

    answers = {}

    for index, question in enumerate(
        quiz["questions"],
        start=1
    ):

        st.markdown(
            f"### Q{index}. {question['question']}"
        )

        options = question["options"]

        answers[index] = st.radio(
            "Select your answer:",
            options=list(options.keys()),
            format_func=lambda key: (
                f"{key}. {options[key]}"
            ),
            key=f"question_{index}"
        )

    if st.button(
        "✅ Submit Quiz",
        type="primary"
    ):

        score = 0

        for index, question in enumerate(
            quiz["questions"],
            start=1
        ):

            if answers[index] == question["correct_answer"]:
                score += 1

        total = len(quiz["questions"])
        percentage = (score / total) * 100 if total else 0

        result_id = save_quiz_result(
            quiz_id=st.session_state["quiz_id"],
            user_id=USER_ID,
            score=score,
            total_questions=total
        )

        st.session_state["quiz_result_id"] = result_id

        st.success(
            f"Quiz completed! Score: {score}/{total}"
        )

        st.metric(
            "Percentage",
            f"{percentage:.1f}%"
        )

# ============================================================
# PROGRESS
# ============================================================

elif page == "📊 Progress":

    st.title("📊 Study Progress")

    st.markdown(
        """
<div class="hero-card">
    <div class="hero-kicker">PERFORMANCE CENTER</div>
    <div class="hero-title">Your learning journey</div>
    <div class="hero-subtitle">
        Track quiz performance, attempts and your best results.
    </div>
</div>
        """,
        unsafe_allow_html=True
    )

    results = get_quiz_results(USER_ID)

    if not results:

        st.info(
            "No quiz results available yet. Complete a quiz to see your progress."
        )

    else:

        total_attempts = len(results)

        average_score = (
            sum(result["percentage"] for result in results)
            / total_attempts
        )

        best_score = max(
            result["percentage"]
            for result in results
        )

        # Performance label
        if average_score >= 80:
            progress_status = "Excellent 🌟"
        elif average_score >= 60:
            progress_status = "Good 👍"
        else:
            progress_status = "Keep Practicing 📖"

        # Top stats
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "📝 Quiz Attempts",
                total_attempts
            )

        with col2:
            st.metric(
                "🎯 Average Score",
                f"{average_score:.1f}%"
            )

        with col3:
            st.metric(
                "🏆 Best Score",
                f"{best_score:.1f}%"
            )

        with col4:
            st.metric(
                "📈 Status",
                progress_status
            )

        st.subheader("📊 Performance Overview")

        overview_col1, overview_col2 = st.columns(2)

        with overview_col1:

            st.markdown("#### Average Performance")

            st.progress(
                min(average_score / 100, 1.0)
            )

            st.caption(
                f"Average quiz performance: {average_score:.1f}%"
            )

        with overview_col2:

            st.markdown("#### Best Performance")

            st.progress(
                min(best_score / 100, 1.0)
            )

            st.caption(
                f"Highest recorded score: {best_score:.1f}%"
            )

        st.divider()

        st.subheader("📚 Quiz History")

        for result in results:

            percentage = result["percentage"]

            if percentage >= 80:
                badge = "🌟 Excellent"
            elif percentage >= 60:
                badge = "👍 Good"
            else:
                badge = "📖 Needs Practice"

            with st.container(border=True):

                st.markdown(
                    f"### 📘 {result['topic']}"
                )

                st.caption(
                    f"Difficulty: {result['difficulty']}"
                )

                score_col1, score_col2 = st.columns(2)

                with score_col1:
                    st.metric(
                        "Score",
                        f"{result['score']}/{result['total_questions']}"
                    )

                with score_col2:
                    st.metric(
                        "Percentage",
                        f"{percentage:.1f}%"
                    )

                st.progress(
                    min(percentage / 100, 1.0)
                )

                st.write(badge)

                st.caption(
                    f"Completed: {result['completed_at']}"
                )





# ============================================================
# STUDY HISTORY
# ============================================================

elif page == "🕒 Study History":

    st.title("🕒 Study History")

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">LEARNING TIMELINE</div>
            <div class="hero-title">Your study activity</div>
            <div class="hero-subtitle">
                Review your recent study sessions and learning time.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    sessions = get_study_sessions(USER_ID)

    if not sessions:

        st.info(
            "No study sessions found yet."
        )

    else:

        total_history_minutes = sum(
            session["duration_minutes"]
            for session in sessions
        )

        history_col1, history_col2 = st.columns(2)

        with history_col1:
            st.metric(
                "📚 Sessions Recorded",
                len(sessions)
            )

        with history_col2:
            st.metric(
                "⌛ Total Study Time",
                f"{total_history_minutes} min"
            )

        st.divider()

        st.subheader("🗓️ Recent Activity")

        for session in sessions:

            subject_name = (
                session["subject_name"]
                if session["subject_name"]
                else "No Subject"
            )

            with st.container(border=True):

                top_col1, top_col2 = st.columns(
                    [3, 1]
                )

                with top_col1:
                    st.markdown(
                        f"### 📘 {subject_name}"
                    )

                    st.write(
                        f"**Topic:** {session['topic']}"
                    )

                with top_col2:
                    st.metric(
                        "Duration",
                        f"{session['duration_minutes']} min"
                    )

                st.caption(
                    f"🕒 {session['session_date']}"
                )


# ============================================================
# STUDY SESSION
# ============================================================

elif page == "⏱️ Study Session":

    st.title("⏱️ Study Session")

    st.markdown(
        """
        ### 🎯 Focus Mode
        Record your learning time and keep building your study streak.
        """
    )

    subjects = get_subjects(USER_ID)

    subject_options = {
        subject["subject_name"]: subject["subject_id"]
        for subject in subjects
    }

    if subject_options:

        col1, col2 = st.columns(2)

        with col1:
            selected_subject = st.selectbox(
                "📚 Select Subject",
                list(subject_options.keys())
            )

        with col2:
            duration = st.number_input(
                "⏱️ Duration (minutes)",
                min_value=1,
                max_value=600,
                value=30,
                step=5
            )

        topic = st.text_input(
            "📖 Topic Studied",
            placeholder="Example: Python Functions"
        )

        st.markdown("###")

        if st.button(
            "🚀 Save Study Session",
            type="primary",
            use_container_width=True
        ):

            if not topic.strip():

                st.warning(
                    "Please enter the topic you studied."
                )

            else:

                session_id = add_study_session(
                    user_id=USER_ID,
                    subject_id=subject_options[selected_subject],
                    topic=topic,
                    duration_minutes=duration
                )

                st.success(
                    f"Study session saved successfully! Session ID: {session_id}"
                )

                st.balloons()

    else:

        st.info(
            "No subjects available. Please add a subject first."
        )
