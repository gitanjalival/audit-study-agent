"""
quiz.py — Practice question loading and algorithm-driven selection.

Selection algorithm: weighted random sampling where each question's
probability is proportional to its topic's combined_weight
(recency × inverse performance). Topics you're weak at AND recently
covered appear most often — implementing the interleaving + retrieval
practice principles from Roediger & Karpicke (2006) and Kornell &
Bjork (2008).
"""

import json
import os
import random

SCRIPT_DIR     = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(SCRIPT_DIR, "questions_cache.json")

XP_CORRECT = 30
XP_ATTEMPT = 5   # wrong answers still earn a little — effort matters


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_questions() -> list:
    """Load questions from cache. Returns empty list if not found."""
    if not os.path.exists(QUESTIONS_FILE):
        return []
    with open(QUESTIONS_FILE) as f:
        data = json.load(f)
    return data.get("questions", [])


# ---------------------------------------------------------------------------
# Algorithm-driven selection
# ---------------------------------------------------------------------------

def get_weighted_questions(all_questions: list,
                            progress: dict,
                            all_cards: list,
                            n: int = 5) -> list:
    """
    Select n questions using the combined recency × performance algorithm.

    Steps:
      1. Get topic weights from schedule (recency × inverse accuracy)
      2. Score each question by its topic weight
      3. Boost questions the user has never seen before (+30%)
      4. Weighted random selection without replacement
    """
    if not all_questions:
        return []

    from schedule import get_weighted_topics_with_performance
    result   = get_weighted_topics_with_performance(progress, all_cards, num_questions=50)
    tw       = {e["topic"]: e["combined_weight"] for e in result.get("topic_plan", [])}
    attempts = progress.get("quiz_attempts", {})

    scored = []
    for q in all_questions:
        base_w = tw.get(q.get("topic", ""), 1.0)
        if attempts.get(q["id"], 0) == 0:
            base_w *= 1.3          # unseen questions get a small boost
        scored.append((q, base_w))

    # Weighted random sampling without replacement
    selected  = []
    remaining = scored[:]
    for _ in range(min(n, len(remaining))):
        total = sum(w for _, w in remaining) or 1
        r     = random.uniform(0, total)
        cum   = 0.0
        for i, (q, w) in enumerate(remaining):
            cum += w
            if r <= cum:
                selected.append(q)
                remaining.pop(i)
                break

    return selected


# ---------------------------------------------------------------------------
# Interleaving
# ---------------------------------------------------------------------------

def build_interleaved_queue(cards: list, questions: list, ratio: int = 3) -> list:
    """
    Interleave flashcards and quiz questions at cards-per-question ratio.

    Result is a mixed list where each item has a 'type' key:
      type='card'  → regular SM-2 flashcard
      type='quiz'  → MC practice question
    """
    queue   = []
    ci, qi  = 0, 0
    while ci < len(cards) or qi < len(questions):
        for _ in range(ratio):
            if ci < len(cards):
                item = dict(cards[ci]); item["type"] = "card"
                queue.append(item); ci += 1
        if qi < len(questions):
            item = dict(questions[qi]); item["type"] = "quiz"
            queue.append(item); qi += 1
    return queue


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def record_quiz_attempt(progress: dict, question_id: str, correct: bool) -> dict:
    """Track per-question attempt counts and correct counts."""
    if "quiz_attempts" not in progress: progress["quiz_attempts"] = {}
    if "quiz_correct"  not in progress: progress["quiz_correct"]  = {}
    progress["quiz_attempts"][question_id] = progress["quiz_attempts"].get(question_id, 0) + 1
    if correct:
        progress["quiz_correct"][question_id] = progress["quiz_correct"].get(question_id, 0) + 1
    return progress
