"""
agent.py — Claude-powered AI logic for the Audit Study Agent.

Three core functions:
  1. generate_summary       — concise structured summary of today's materials
  2. generate_study_plan    — spaced-repetition daily study schedule
  3. generate_practice_questions — professor-stylized Q&A from notes + past quizzes
"""

import anthropic


def _client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# 1. Material Summarizer
# ---------------------------------------------------------------------------

def generate_summary(api_key: str, materials_text: str) -> str:
    """
    Summarize course materials into a concise, exam-ready overview.

    Args:
        api_key:        Anthropic API key
        materials_text: concatenated text from selected course files

    Returns:
        Markdown-formatted summary string
    """
    client = _client(api_key)

    prompt = f"""You are a study assistant helping a Notre Dame student in an Auditing class.

Below are materials from a recent class session. Generate a concise, structured summary that a student can review in 10–15 minutes.

Your summary should:
1. Open with a 2–3 sentence "Big Picture" of what this session covered
2. List the most important concepts, definitions, and standards (GAAS, PCAOB, ASC, etc.)
3. Highlight key rules, procedures, or frameworks introduced
4. Note any connections to prior material or real-world applications
5. End with a short "Likely Exam Topics" bullet list

Use clear headers (##) and bullet points. Be concise — prioritize retention over comprehensiveness.

---
COURSE MATERIALS:
{materials_text}
---

Generate the summary:"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# 2. Study Plan Generator
# ---------------------------------------------------------------------------

def generate_study_plan(
    api_key: str,
    materials_text: str,
    next_class_date: str,
    exam_date: str,
    hours_per_day: float,
    focus_areas: str = "",
) -> str:
    """
    Build a personalized daily study plan using evidence-based strategies
    (spaced repetition, interleaving, active recall).

    Args:
        api_key:          Anthropic API key
        materials_text:   concatenated text from all course materials
        next_class_date:  date of next class (string, YYYY-MM-DD)
        exam_date:        upcoming exam or quiz date (string, YYYY-MM-DD)
        hours_per_day:    study hours available per day
        focus_areas:      optional string of topics the student wants to prioritize

    Returns:
        Markdown-formatted daily study plan
    """
    client = _client(api_key)

    focus_block = (
        f"\nTopics the student wants to prioritize: {focus_areas}" if focus_areas.strip() else ""
    )

    prompt = f"""You are an expert study coach helping a Notre Dame Auditing student prepare for exams.

Use the following evidence-based strategies:
- **Spaced repetition**: schedule reviews of older material at increasing intervals
- **Interleaving**: mix different topics within each session rather than blocking
- **Active recall**: include specific retrieval activities (flashcards, practice problems, blank-page recall) — not re-reading

STUDENT CONTEXT:
- Next class: {next_class_date}
- Exam / quiz date: {exam_date}
- Available study time: {hours_per_day} hours per day{focus_block}

COURSE MATERIALS TO COVER:
{materials_text}

Create a day-by-day study plan from today until the exam. For each day include:
- A theme / focus area
- Specific tasks with estimated time (e.g., "20 min — blank-page recall of internal controls framework")
- At least one active recall activity per session
- A brief note on *why* this order makes sense (spacing, interleaving, etc.)

Keep the total daily time at or under {hours_per_day} hours.
Format cleanly with a ## header for each day.

Generate the study plan:"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# 3. Practice Question Generator
# ---------------------------------------------------------------------------

def generate_practice_questions(
    api_key: str,
    notes_text: str,
    quiz_examples: str,
    num_questions: int = 20,
    question_types: list | None = None,
    difficulty: str = "Mixed",
    include_answers: bool = True,
    topic_plan: list[dict] | None = None,   # from schedule.get_weighted_topics()
) -> list[dict]:
    """
    Generate professor-stylized practice questions as structured JSON for interactive grading.

    Returns a list of question dicts:
      {
        "type": "mc" | "short_answer" | "true_false",
        "question": "...",
        "options": ["A. ...", "B. ...", "C. ...", "D. ..."],  # MC/TF only
        "correct": "A" | "True" | "short answer text",
        "explanation": "..."
      }
    """
    import json as _json

    client = _client(api_key)

    if question_types is None:
        question_types = ["Multiple Choice", "Short Answer"]

    type_map = {
        "Multiple Choice": "mc",
        "True/False": "true_false",
        "Short Answer": "short_answer",
        "Problem-Solving": "short_answer",
        "Essay": "short_answer",
    }
    types_requested = [type_map.get(t, "short_answer") for t in question_types]

    if quiz_examples.strip():
        style_block = (
            f"PROFESSOR MORRISON'S PAST QUIZZES & PRACTICE PROBLEMS\n"
            f"Study this carefully. It serves two purposes:\n"
            f"  (A) STYLE: Mirror the terminology, scenario framing, and difficulty EXACTLY.\n"
            f"  (B) TOPIC SIGNAL: These materials reveal which concepts the professor "
            f"actually tests. Identify the most-tested topics and BOOST question weight "
            f"toward them — even when they appear in lower-recency schedule slots.\n\n"
            f"{quiz_examples}\n\n---"
        )
        professor_focus_note = (
            "PROFESSOR FOCUS OVERRIDE: Where the past quizzes/practice problems emphasize "
            "a concept heavily (e.g. precision of controls, direction of testing, audit risk "
            "model, assertions), treat that concept as HIGH PRIORITY regardless of recency "
            "weighting. The spaced-repetition allocation sets the floor; professor focus can "
            "increase a topic's share."
        )
    else:
        style_block = "Use a rigorous upper-level Notre Dame Auditing course style."
        professor_focus_note = ""

    # Build topic allocation instructions from the weighted plan
    if topic_plan:
        topic_lines = []
        for entry in topic_plan:
            if entry["num_questions"] > 0 and entry["concepts"]:
                concepts_str = ", ".join(entry["concepts"][:8])
                topic_lines.append(
                    f"  - {entry['num_questions']} question(s) on Class {entry['class_num']} "
                    f"— {entry['topic']}: [{concepts_str}]"
                )
        topic_instruction = (
            "TOPIC ALLOCATION (spaced repetition weighted by recency — treat as a floor, "
            "not a ceiling; professor focus topics may receive additional questions):\n"
            + "\n".join(topic_lines)
        )
    else:
        topic_instruction = "Cover a balanced spread of topics from the course notes."

    focus_section = f"\n{professor_focus_note}\n" if professor_focus_note else ""

    prompt = f"""You are generating high-quality exam practice questions for a Notre Dame student in ACCT 40510 Auditing (Prof. Morrison, Spring 2026).

{style_block}

COURSE NOTES AND MATERIALS:
{notes_text}

---

{topic_instruction}
{focus_section}
QUESTION SPECIFICATIONS:
- Total questions: exactly {num_questions}
- Types to use: {", ".join(question_types)}
- Difficulty: {difficulty}

QUALITY STANDARDS — follow these strictly:
1. Multiple choice distractors must be PLAUSIBLE. Wrong answers should represent common misconceptions or subtle misunderstandings, not obvious nonsense.
2. Questions must test UNDERSTANDING, not just memorization. Use scenario-based framing where possible (e.g. "An auditor is reviewing XYZ. Which of the following...").
3. Mirror Prof. Morrison's style from the quiz examples: precise technical language, PCAOB/GAAS terminology, realistic audit scenarios.
4. Short answer questions must require the student to APPLY a concept, not just define it.
5. Never write a question and answer that give away the answer (e.g. don't repeat a key term from the question in the correct answer).
6. For MC: all 4 options must be grammatically parallel and similar in length.
7. Explanations must explain WHY the correct answer is right AND briefly why the main wrong answer is wrong.
8. If a concept appears in BOTH the practice problems/past quizzes AND the recent class material, prioritize it — it is both professor-tested and freshly covered.

Return ONLY a valid JSON array — no markdown fences, no text outside the array.
Each element must follow this exact schema:

Multiple choice:
{{"type": "mc", "question": "Full scenario-based question text ending with a question?", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "correct": "A", "explanation": "Why A is correct. Why the most tempting wrong answer fails."}}

True/false:
{{"type": "true_false", "question": "Statement to evaluate as true or false.", "options": ["True", "False"], "correct": "True", "explanation": "Why this is true/false with the key technical reasoning."}}

Short answer:
{{"type": "short_answer", "question": "Scenario-based question requiring 2-4 sentence applied response.", "options": [], "correct": "Full model answer demonstrating the expected level of detail.", "explanation": "Key concepts the answer must address to receive full credit."}}

Start your response with [ and end with ]. Nothing else."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=7000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    return _json.loads(raw)


# ---------------------------------------------------------------------------
# 4. Session Debrief Generator
# ---------------------------------------------------------------------------

def generate_session_debrief(api_key: str, session_results: list) -> str:
    """
    Generate a 3-sentence personalized debrief after a practice session.
    session_results: list of dicts with keys: question, topic, correct (bool),
                     chosen (str), correct_answer (str), explanation (str)
    """
    client = _client(api_key)
    correct_count = sum(1 for r in session_results if r.get("correct"))
    total = len(session_results)

    results_lines = []
    for r in session_results:
        status = "CORRECT" if r.get("correct") else f"WRONG (chose: {r.get('chosen','?')}, right: {r.get('correct_answer','?')})"
        results_lines.append(f"  [{r.get('topic','?')}] {r.get('question','')[:90]}... → {status}")

    prompt = f"""You are a study coach for a Notre Dame student in ACCT 40510 Auditing (Prof. Morrison).

The student just completed a {total}-question practice session and got {correct_count}/{total} correct.

Session results:
{chr(10).join(results_lines)}

Write EXACTLY 3 sentences — no more, no less:
1. Acknowledge their strongest performance area (name the specific topic or concept)
2. Identify the single most important gap exposed by this session (specific concept or distinction they missed)
3. Give ONE concrete action: name the exact concept, standard, or distinction to review next

Rules:
- Be direct. No filler like "Great job!"
- Use precise auditing terminology (PCAOB, GAAS, assertions, etc.)
- If they got everything right, still find a nuance or edge case to mention
- Plain prose only. No bullet points, headers, or markdown."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=250,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_tutor_response(
    api_key: str,
    question_text: str,
    correct_answer: str,
    explanation: str,
    user_question: str,
    topic: str,
) -> str:
    """Answer a follow-up question about a specific practice question."""
    client = _client(api_key)
    prompt = f"""You are a precise, patient tutor for a Notre Dame student in ACCT 40510 Auditing.

The student just answered this practice question:
TOPIC: {topic}
QUESTION: {question_text}
CORRECT ANSWER: {correct_answer}
EXPLANATION: {explanation}

The student is asking: "{user_question}"

Answer in 2–4 sentences. Be specific and use correct auditing terminology. If they are confused about a distinction, explain both sides clearly. Do not start with filler phrases like "Great question!" — just answer directly."""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=350,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
