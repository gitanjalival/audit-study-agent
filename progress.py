"""
progress.py — Study progress tracking for the Audit Study Agent.

Tracks:
  - SM-2 scheduling state per card (via flashcards.sm2_update)
  - Daily streak (habit loop: Clear, 2018; Duhigg, 2012)
  - Per-topic accuracy for weak-spot identification
    (metacognitive awareness improves study efficiency: Dunlosky et al., 2013)

Storage: primary = st.session_state (works on Streamlit Cloud),
         secondary = study_progress.json (persists locally).
"""

import json
import os
from datetime import date, timedelta
from math import exp

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(SCRIPT_DIR, "study_progress.json")

_DEFAULTS: dict = {
    "last_study_date":  None,
    "last_reset_date":  None,
    "streak":           0,
    "longest_streak":   0,
    "total_reviews":    0,
    "cards_today":      0,
    "correct_today":    0,
    "cards":            {},
}


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def load_progress() -> dict:
    """Load from file if available, otherwise return defaults."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                data = json.load(f)
            for k, v in _DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return _DEFAULTS.copy()


def save_progress(progress: dict) -> None:
    """Save to file (silently skips on read-only filesystems like Streamlit Cloud)."""
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Streak & Daily Tracking
# ---------------------------------------------------------------------------

def _refresh_daily(progress: dict) -> dict:
    """Reset daily counters at midnight."""
    today = date.today().isoformat()
    if progress.get("last_reset_date") != today:
        progress["cards_today"]      = 0
        progress["correct_today"]    = 0
        progress["last_reset_date"]  = today
    return progress


def update_streak(progress: dict) -> dict:
    """
    Increment streak if studied yesterday, reset if gap > 1 day.
    Same-day studies don't double-count.
    """
    today     = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last      = progress.get("last_study_date")

    if last == yesterday:
        progress["streak"] += 1
    elif last != today:
        progress["streak"] = 1  # streak broken or first day

    progress["longest_streak"] = max(progress.get("longest_streak", 0), progress["streak"])
    progress["last_study_date"] = today
    return progress


# ---------------------------------------------------------------------------
# Recording Reviews
# ---------------------------------------------------------------------------

def record_review(progress: dict, card_id: str, rating: int) -> dict:
    """
    Record one card review:
      - Updates SM-2 scheduling data
      - Increments daily / total counters
      - Updates streak
    """
    from flashcards import sm2_update  # local import to avoid circular dependency

    today    = date.today().isoformat()
    progress = _refresh_daily(progress)
    progress = update_streak(progress)

    progress["total_reviews"]  = progress.get("total_reviews", 0)  + 1
    progress["cards_today"]    = progress.get("cards_today", 0)    + 1
    if rating >= 3:
        progress["correct_today"] = progress.get("correct_today", 0) + 1

    card_data = progress["cards"].get(card_id, {})
    card_data = sm2_update(card_data, rating)
    card_data.setdefault("history", []).append({"date": today, "rating": rating})
    progress["cards"][card_id] = card_data

    return progress


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def get_today_stats(progress: dict) -> dict:
    progress = _refresh_daily(progress)
    return {
        "cards_today":    progress.get("cards_today", 0),
        "correct_today":  progress.get("correct_today", 0),
        "streak":         progress.get("streak", 0),
        "longest_streak": progress.get("longest_streak", 0),
        "total_reviews":  progress.get("total_reviews", 0),
    }


def get_weak_spots(progress: dict, all_cards: list) -> list:
    """
    Return topics sorted by accuracy ascending (worst first).
    Only includes topics with at least 3 total reviews.
    """
    stats: dict = {}

    for card in all_cards:
        cid     = card["id"]
        topic   = card.get("topic", "Unknown")
        history = progress.get("cards", {}).get(cid, {}).get("history", [])
        if not history:
            continue

        s = stats.setdefault(topic, {
            "correct":   0,
            "total":     0,
            "class_num": card.get("class_num", 0),
        })
        for r in history:
            s["total"] += 1
            if r["rating"] >= 3:
                s["correct"] += 1

    result = [
        {
            "topic":     topic,
            "accuracy":  s["correct"] / s["total"],
            "correct":   s["correct"],
            "total":     s["total"],
            "class_num": s["class_num"],
        }
        for topic, s in stats.items()
        if s["total"] >= 3
    ]

    return sorted(result, key=lambda x: x["accuracy"])


def get_all_topic_stats(progress: dict, all_cards: list) -> list:
    """Return all topics with accuracy data, sorted best → worst."""
    return list(reversed(get_weak_spots(progress, all_cards)))


# ---------------------------------------------------------------------------
# XP & Gamification
# ---------------------------------------------------------------------------

DAILY_GOAL_XP = 200

XP_FOR_RATING: dict = {1: 0, 2: 10, 3: 25, 4: 40}

ACHIEVEMENTS: dict = {
    "first_card":      {"name": "First Step",    "desc": "Reviewed your first card"},
    "streak_3":        {"name": "On a Roll",      "desc": "3-day study streak"},
    "streak_7":        {"name": "Locked In",      "desc": "7-day study streak"},
    "streak_14":       {"name": "Unstoppable",    "desc": "14-day study streak"},
    "daily_goal":      {"name": "Daily Goal",     "desc": "Hit 200 XP in a single day"},
    "perfect_session": {"name": "Clean Sweep",    "desc": "All Good or Easy in a session (5+ cards)"},
    "cards_25":        {"name": "Warming Up",     "desc": "Reviewed 25 cards total"},
    "cards_100":       {"name": "Card Shark",     "desc": "Reviewed 100 cards total"},
    "cards_250":       {"name": "Audit Ready",    "desc": "Reviewed 250 cards total"},
}


def get_xp_today(progress: dict) -> int:
    """Return XP earned today."""
    today = date.today().isoformat()
    return progress.get("xp_by_day", {}).get(today, 0)


def add_xp(progress: dict, xp: int) -> dict:
    """Add XP to today's total and lifetime total."""
    today = date.today().isoformat()
    if "xp_by_day" not in progress:
        progress["xp_by_day"] = {}
    progress["xp_by_day"][today] = progress["xp_by_day"].get(today, 0) + xp
    progress["xp_total"] = progress.get("xp_total", 0) + xp
    return progress


def check_new_achievements(progress: dict, session_ratings: list | None = None) -> list:
    """
    Check for newly earned achievements. Returns list of new achievement IDs.
    Updates progress["achievements"] in place if new ones were earned.
    """
    earned = set(progress.get("achievements", []))
    new: list = []

    def earn(aid: str) -> None:
        if aid not in earned:
            new.append(aid)
            earned.add(aid)

    total = progress.get("total_reviews", 0)
    if total >= 1:   earn("first_card")
    if total >= 25:  earn("cards_25")
    if total >= 100: earn("cards_100")
    if total >= 250: earn("cards_250")

    streak = progress.get("streak", 0)
    if streak >= 3:  earn("streak_3")
    if streak >= 7:  earn("streak_7")
    if streak >= 14: earn("streak_14")

    if get_xp_today(progress) >= DAILY_GOAL_XP:
        earn("daily_goal")

    if session_ratings and len(session_ratings) >= 5:
        if all(r >= 3 for r in session_ratings):
            earn("perfect_session")

    if new:
        progress["achievements"] = list(earned)
    return new


def record_misconception(progress: dict, topic: str, chosen_text: str, correct_text: str) -> dict:
    """
    Record a specific wrong answer pattern.
    chosen_text / correct_text should be the SHORT option label (e.g. "A. Significant deficiency").
    """
    if "misconceptions" not in progress:
        progress["misconceptions"] = {}
    tm = progress["misconceptions"].setdefault(topic, {})
    key = f"{chosen_text[:60]} → {correct_text[:60]}"
    tm[key] = tm.get(key, 0) + 1
    return progress


def get_top_misconceptions(progress: dict, top_n: int = 5) -> list:
    """
    Return top N most-repeated wrong-answer patterns across all topics.
    Each item: {"topic": str, "confusion": str, "count": int}
    """
    miscons = progress.get("misconceptions", {})
    flat = [
        {"topic": topic, "confusion": confusion, "count": count}
        for topic, confusions in miscons.items()
        for confusion, count in confusions.items()
    ]
    return sorted(flat, key=lambda x: x["count"], reverse=True)[:top_n]


def get_forgetting_predictions(progress: dict, all_cards: list) -> list:
    """
    Predict current memory retention per topic using exponential decay
    (Ebbinghaus forgetting curve approximation based on SM-2 intervals).

    retention ≈ e^(-days_since_review / stability)
    where stability ≈ interval × 1.5

    Returns list of {topic, retention, days_since, interval, card_count}
    sorted by retention ascending (most forgotten first).
    Only includes topics where at least one card has been reviewed.
    """
    today = date.today()
    topic_data: dict = {}

    for card in all_cards:
        cid   = card["id"]
        topic = card.get("topic", "Unknown")
        cp    = progress.get("cards", {}).get(cid, {})
        if not cp or cp.get("repetitions", 0) == 0:
            continue  # never reviewed

        interval    = cp.get("interval", 1)
        next_review = cp.get("next_review")
        if not next_review:
            continue
        try:
            next_rev_date = date.fromisoformat(next_review)
        except Exception:
            continue

        last_review_date = next_rev_date - timedelta(days=interval)
        days_since       = max(0, (today - last_review_date).days)
        stability        = max(1, interval * 1.5)
        retention        = max(0.05, min(1.0, exp(-days_since / stability)))

        td = topic_data.setdefault(topic, {"retentions": [], "days_since_list": [], "interval_list": []})
        td["retentions"].append(retention)
        td["days_since_list"].append(days_since)
        td["interval_list"].append(interval)

    result = []
    for topic, td in topic_data.items():
        avg_ret    = sum(td["retentions"]) / len(td["retentions"])
        avg_days   = sum(td["days_since_list"]) / len(td["days_since_list"])
        avg_int    = sum(td["interval_list"]) / len(td["interval_list"])
        result.append({
            "topic":      topic,
            "retention":  round(avg_ret, 3),
            "days_since": round(avg_days, 1),
            "interval":   round(avg_int, 1),
            "card_count": len(td["retentions"]),
        })

    return sorted(result, key=lambda x: x["retention"])


def get_weekly_stats(progress: dict, all_cards: list) -> dict:
    """
    Aggregate study stats for the past 7 days for weekly synthesis.
    Returns dict with xp_by_day, total_xp, avg_accuracy, topic_trends, streak, etc.
    """
    today = date.today()

    # XP per day for last 7 days
    xp_by_day = {}
    for i in range(7):
        d = (today - timedelta(days=i)).isoformat()
        xp_by_day[d] = progress.get("xp_by_day", {}).get(d, 0)

    # Per-topic accuracy over last 7 days
    topic_stats: dict = {}
    cutoff = (today - timedelta(days=7)).isoformat()
    for card in all_cards:
        cid   = card["id"]
        topic = card.get("topic", "Unknown")
        history = progress.get("cards", {}).get(cid, {}).get("history", [])
        recent = [h for h in history if h.get("date", "") >= cutoff]
        if not recent:
            continue
        ts = topic_stats.setdefault(topic, {"correct": 0, "total": 0})
        for h in recent:
            ts["total"] += 1
            if h.get("rating", 0) >= 3:
                ts["correct"] += 1

    topic_accuracy = {
        t: round(s["correct"] / s["total"], 3)
        for t, s in topic_stats.items() if s["total"] >= 2
    }

    quiz_attempts = progress.get("quiz_attempts", {})
    quiz_correct  = progress.get("quiz_correct", {})
    quiz_acc = (sum(quiz_correct.values()) / sum(quiz_attempts.values())
                if sum(quiz_attempts.values()) > 0 else None)

    return {
        "xp_by_day":      xp_by_day,
        "total_xp_week":  sum(xp_by_day.values()),
        "topic_accuracy": topic_accuracy,
        "quiz_accuracy":  quiz_acc,
        "streak":         progress.get("streak", 0),
        "total_reviews":  progress.get("total_reviews", 0),
        "days_studied":   sum(1 for xp in xp_by_day.values() if xp > 0),
    }


def streak_calendar(progress: dict, days: int = 7) -> list[dict]:
    """
    Return last N days as list of {date, studied} dicts for the calendar strip.
    """
    cards = progress.get("cards", {})
    studied_dates: set = set()
    for card_data in cards.values():
        for entry in card_data.get("history", []):
            studied_dates.add(entry["date"])

    result = []
    for i in range(days - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        result.append({"date": d, "studied": d in studied_dates})
    return result


# ─────────────────────────────────────────────────────────────────
# FEATURE 5: Study-time Performance Tracking
# ─────────────────────────────────────────────────────────────────

def record_time_accuracy(progress: dict, correct: bool) -> dict:
    """Record whether a practice answer was correct, keyed by hour of day."""
    from datetime import datetime
    hour = datetime.now().hour
    # Bucket: 0=midnight-6, 1=6am-12pm, 2=12pm-6pm, 3=6pm-midnight
    bucket = hour // 6  # 0,1,2,3
    if "time_accuracy" not in progress:
        progress["time_accuracy"] = {}
    key = str(bucket)
    ta  = progress["time_accuracy"].setdefault(key, {"correct": 0, "total": 0})
    ta["total"] += 1
    if correct:
        ta["correct"] += 1
    return progress


def get_time_of_day_stats(progress: dict) -> list:
    """
    Return accuracy by time-of-day bucket.
    Each item: {label, correct, total, accuracy}
    """
    labels = {
        "0": "Midnight – 6am",
        "1": "Morning (6am–12pm)",
        "2": "Afternoon (12–6pm)",
        "3": "Evening (6–midnight)",
    }
    ta = progress.get("time_accuracy", {})
    result = []
    for key, label in labels.items():
        if key in ta and ta[key]["total"] >= 3:
            s = ta[key]
            result.append({
                "label":    label,
                "correct":  s["correct"],
                "total":    s["total"],
                "accuracy": round(s["correct"] / s["total"], 3),
            })
    return sorted(result, key=lambda x: x["accuracy"], reverse=True)
