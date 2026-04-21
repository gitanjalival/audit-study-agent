"""
flashcards.py — Flashcard generation + SM-2 spaced repetition for the Audit Study Agent.

Research basis:
  - Ebbinghaus (1885): forgetting curve — spaced practice dramatically reduces forgetting
  - Cepeda et al. (2006): optimal spacing increases long-term retention by 200%+
  - SM-2 algorithm (Wozniak, 1987): the scheduling algorithm behind Anki and SuperMemo
  - Kornell & Bjork (2008): interleaved practice improves transfer over blocked practice
"""

import json
import os
from datetime import date, timedelta

import anthropic

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_FILE = os.path.join(SCRIPT_DIR, "flashcards_cache.json")


# ---------------------------------------------------------------------------
# SM-2 Spaced Repetition Algorithm
# ---------------------------------------------------------------------------

def sm2_update(card_data: dict, rating: int) -> dict:
    """
    Update card scheduling using SM-2 (Wozniak, 1987).

    rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    Returns updated card_data dict with next_review date.
    """
    easiness = card_data.get("easiness", 2.5)
    interval = card_data.get("interval", 1)
    reps     = card_data.get("repetitions", 0)

    if rating < 3:
        # Failed — reset repetitions, review tomorrow
        reps     = 0
        interval = 1
    else:
        if   reps == 0: interval = 1
        elif reps == 1: interval = 6
        else:           interval = max(1, round(interval * easiness))
        reps += 1

    # Adjust easiness factor (stays above 1.3 to prevent interval collapse)
    easiness = max(1.3, easiness + 0.1 - (4 - rating) * (0.08 + (4 - rating) * 0.02))

    return {
        "easiness":    round(easiness, 2),
        "interval":    interval,
        "repetitions": reps,
        "next_review": (date.today() + timedelta(days=interval)).isoformat(),
    }


def get_due_cards(all_cards: list, progress: dict, max_new: int = 15, max_review: int = 25) -> list:
    """
    Build today's study queue.

    Priority: overdue reviews first (sorted by how overdue), then new cards.
    Caps new cards at max_new to prevent overwhelm — research shows introducing
    too many new items at once degrades retention (Kornell & Bjork, 2008).
    """
    today = date.today().isoformat()
    due   = []
    new   = []

    for card in all_cards:
        cid       = card["id"]
        cp        = progress.get("cards", {}).get(cid, {})
        next_rev  = cp.get("next_review", today)
        is_new    = cp.get("repetitions", 0) == 0

        if is_new:
            new.append(card)
        elif next_rev <= today:
            due.append(card)

    # Most overdue cards first
    due.sort(key=lambda c: progress.get("cards", {}).get(c["id"], {}).get("next_review", today))

    return due[:max_review] + new[:max_new]


def count_due(all_cards: list, progress: dict) -> dict:
    """Return counts of due-for-review and new cards."""
    today = date.today().isoformat()
    n_due = n_new = 0
    for card in all_cards:
        cp = progress.get("cards", {}).get(card["id"], {})
        if cp.get("repetitions", 0) == 0:
            n_new += 1
        elif cp.get("next_review", today) <= today:
            n_due += 1
    return {"due": n_due, "new": n_new}


# ---------------------------------------------------------------------------
# Flashcard Generation via Claude
# ---------------------------------------------------------------------------

def generate_flashcards(api_key: str, materials_text: str, topic_plan: list) -> list:
    """
    Generate 50 high-quality Anki-style flashcards from course materials.
    Cards are interleaved across topics (not blocked by chapter).
    """
    client = anthropic.Anthropic(api_key=api_key)

    topic_lines = [
        f"Class {e['class_num']} — {e['topic']}: {', '.join(e['concepts'][:6])}"
        for e in topic_plan if e.get("concepts")
    ]

    prompt = f"""You are creating Anki-style flashcards for a Notre Dame student in ACCT 40510 Auditing (Prof. Morrison, Spring 2026).

COURSE TOPICS:
{chr(10).join(topic_lines)}

COURSE MATERIALS:
{materials_text}

Create exactly 50 flashcards. Mix these types proportionally:
- Definition (20%): "What is [term]?" → clear, complete definition
- Application (30%): "An auditor encounters X — what should they do and why?"
- Distinction (20%): "What is the difference between X and Y?"
- Rule/Standard (20%): "Under [PCAOB/GAAS/ASC], what does [requirement] state?"
- Scenario (10%): "Given [situation], which assertion is most at risk and why?"

STRICT RULES:
1. FRONT: max 2 sentences. Specific, clear question. No vague "explain" questions.
2. BACK: 2–4 sentences of plain prose. No bullet points. Complete and accurate.
3. Test UNDERSTANDING — not just recall of a definition.
4. Cover all major topics. Don't over-index on early material.
5. ID must be a unique kebab-case slug (e.g. "audit-risk-model-formula").
6. Topic field must match the class topic name exactly.

Return ONLY a valid JSON array. No markdown fences, no text outside the array.
Schema per card: {{"id":"slug","front":"question","back":"answer","topic":"Topic Name","class_num":4}}
Start with [ and end with ]. Nothing else."""

    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    cards = json.loads(raw)

    # De-duplicate IDs
    seen: dict = {}
    for c in cards:
        base = c.get("id", "card")
        if base in seen:
            seen[base] += 1
            c["id"] = f"{base}-{seen[base]}"
        else:
            seen[base] = 0

    return cards


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_flashcards() -> list:
    """Load cards from cache file. Returns empty list if not found."""
    if not os.path.exists(CARDS_FILE):
        return []
    with open(CARDS_FILE) as f:
        data = json.load(f)
    # Support both raw list (legacy) and wrapped dict
    return data if isinstance(data, list) else data.get("cards", [])


def save_flashcards(cards: list):
    """Save cards to cache file with a generated_at timestamp."""
    with open(CARDS_FILE, "w") as f:
        json.dump({"generated_at": date.today().isoformat(), "cards": cards}, f, indent=2)
