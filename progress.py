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
