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


def get_due_cards(all_cards: list, progress: dict, max_new: int = 15, max_review: int = 25,
                  compress_factor: float = 0.0) -> list:
    """
    Build today's study queue.

    Priority: overdue reviews first (sorted by how overdue), then new cards.
    Caps new cards at max_new to prevent overwhelm — research shows introducing
    too many new items at once degrades retention (Kornell & Bjork, 2008).

    FEATURE 4: compress_factor (0.0-1.0) shortens SM-2 intervals when exam is ≤7 days away.
    """
    today     = date.today()
    today_str = today.isoformat()
    due       = []
    new       = []

    for card in all_cards:
        cid      = card["id"]
        cp       = progress.get("cards", {}).get(cid, {})
        next_rev = cp.get("next_review", today_str)
        is_new   = cp.get("repetitions", 0) == 0
        interval = cp.get("interval", 1)

        if is_new:
            new.append(card)
        else:
            if compress_factor > 0 and interval > 1:
                compress_days = int(interval * compress_factor)
                try:
                    next_rev_date    = date.fromisoformat(next_rev)
                    effective_rev    = next_rev_date - timedelta(days=compress_days)
                    effective_rev_str = effective_rev.isoformat()
                except Exception:
                    effective_rev_str = next_rev
            else:
                effective_rev_str = next_rev

            if effective_rev_str <= today_str:
                due.append(card)

    # Most overdue cards first
    due.sort(key=lambda c: progress.get("cards", {}).get(c["id"], {}).get("next_review", today_str))
    return due[:max_review] + new[:max_new]


def count_due(all_cards: list, progress: dict, compress_factor: float = 0.0) -> dict:
    """
    Return counts of due-for-review and new cards.

    FEATURE 4: compress_factor applies interval compression for pre-exam review.
    """
    today     = date.today()
    today_str = today.isoformat()
    n_due = n_new = 0
    for card in all_cards:
        cp = progress.get("cards", {}).get(card["id"], {})
        if cp.get("repetitions", 0) == 0:
            n_new += 1
        else:
            next_rev = cp.get("next_review", today_str)
            interval = cp.get("interval", 1)
            if compress_factor > 0 and interval > 1:
                compress_days = int(interval * compress_factor)
                try:
                    next_rev_date = date.fromisoformat(next_rev)
                    effective_rev = next_rev_date - timedelta(days=compress_days)
                    effective_rev_str = effective_rev.isoformat()
                except Exception:
                    effective_rev_str = next_rev
            else:
                effective_rev_str = next_rev

            if effective_rev_str <= today_str:
                n_due += 1
    return {"due": n_due, "new": n_new}


# ---------------------------------------------------------------------------
# Flashcard Generation via Claude
# ---------------------------------------------------------------------------

def generate_flashcards(api_key: str, materials_text: str, topic_plan: list) -> list:
    """
    Generate 75 definition-first flashcards optimised for SM-2 spaced repetition.

    Research basis:
      - Kornell & Bjork (2008): interleaved, atomic cards beat blocked review
      - Karpicke & Roediger (2008): retrieval practice requires clear right/wrong signal
      - Wozniak SM-2: works best when each card tests exactly one concept
    Cards are weighted toward recent topics so the deck reinforces this week's learning
    first, while still seeding older material for spaced retrieval practice.
    """
    client = anthropic.Anthropic(api_key=api_key)

    # Build per-topic allocation string — recent topics get more cards
    total_w = sum(e.get("weight", 1) for e in topic_plan if e.get("concepts"))
    topic_lines = []
    for e in topic_plan:
        if not e.get("concepts"):
            continue
        alloc = max(1, round(e.get("weight", 1) / total_w * 75))
        topic_lines.append(
            f"  [{alloc} cards] Class {e['class_num']} — {e['topic']}: "
            f"{', '.join(e['concepts'][:8])}"
        )

    prompt = f"""You are building a spaced-repetition flashcard deck for a Notre Dame student in ACCT 40510 Auditing (Prof. Morrison, Spring 2026).

TOPIC ALLOCATION (weighted by recency — recent classes get more cards):
{chr(10).join(topic_lines)}

COURSE MATERIALS:
{materials_text}

─────────────────────────────────────────
CARD FORMAT RULES (critical for SM-2 to work)
─────────────────────────────────────────
Each card must test EXACTLY ONE concept so the student has a clear pass/fail signal.

Use these three types in the proportions shown:

1. DEFINITION (60% of cards)
   Front: "What is [term]?"   OR   "[Term]:" (for pure vocabulary)
   Back: ONE clear sentence defining the term. Add one sentence of context only if essential.
   Good example:
     Front: "What is tolerable misstatement?"
     Back: "The maximum monetary error in an account balance or class of transactions that the auditor can accept without concluding the financial statements are materially misstated. It is always set below planning materiality."

2. DISTINCTION (25% of cards)
   Front: "What is the difference between [X] and [Y]?"
   Back: One sentence on X, one sentence on Y. No more.
   Good example:
     Front: "What is the difference between a significant deficiency and a material weakness?"
     Back: "A significant deficiency is a control deficiency important enough to merit attention but less severe than a material weakness. A material weakness creates a reasonable possibility that a material misstatement will not be prevented or detected on a timely basis."

3. KEY RULE (15% of cards)
   Front: "Under [standard/framework], what is [requirement]?"
   Back: State the rule in plain language in 1–2 sentences.

─────────────────────────────────────────
STRICT QUALITY RULES
─────────────────────────────────────────
1. FRONT: max 15 words. One sharp question, no vague "explain" prompts.
2. BACK: max 3 sentences. Plain prose — NO bullet points, NO sub-lists.
3. Atomic: each card tests ONE thing. If you feel the urge to say "and also…" split it into two cards.
4. Memorable: prefer concrete over abstract. Use numbers, thresholds, and examples where they exist (e.g. "1-day interval → 6-day interval → EF × prior interval").
5. Accurate: every definition must be technically correct for PCAOB / GAAS / ACCT 40510.
6. IDs must be unique kebab-case slugs (e.g. "tolerable-misstatement-def").
7. Topic field must exactly match the class topic name from the allocation list above.
8. Generate exactly 75 cards. Respect the per-topic allocations closely (±1 card per topic is fine).

Return ONLY a valid JSON array. No markdown fences, no text outside the array.
Schema per card:
{{"id":"slug","front":"question text","back":"answer text","topic":"Topic Name","class_num":4}}
Start with [ and end with ]. Nothing else."""

    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    # Attempt to parse; if truncated, recover all complete cards
    try:
        cards = json.loads(raw)
    except json.JSONDecodeError:
        # Find the last complete card object by trimming to the last "},{"
        last_close = raw.rfind("},")
        if last_close == -1:
            last_close = raw.rfind("}")
        if last_close != -1:
            raw = raw[: last_close + 1] + "\n]"
            cards = json.loads(raw)
        else:
            raise

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
