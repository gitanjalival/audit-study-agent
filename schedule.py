"""
schedule.py — Course schedule intelligence for the Audit Study Agent.

Knows the full ACCT 40510 (Spring 2026) schedule, figures out which classes
have been completed as of today, and returns a weighted topic list for
spaced-repetition question generation.

Spaced repetition weighting:
  - Last 1-2 classes  → HIGH weight   (fresh material, needs reinforcement)
  - 3-6 classes ago   → MEDIUM weight (solidifying)
  - 7-14 classes ago  → LOW weight    (review / retrieval practice)
  - 15+ classes ago   → REVIEW weight (long-term retention)
"""

from datetime import date

# ---------------------------------------------------------------------------
# Full course schedule
# Each entry: (class_number, date, topic, key_concepts)
# ---------------------------------------------------------------------------

SCHEDULE = [
    (1,  date(2026, 1, 13), "Introduction & Audit Overview",
     ["role of auditing", "audit vs accounting", "assurance services", "demand for audits"]),

    (2,  date(2026, 1, 15), "Standards & Audit Overview",
     ["GAAS", "PCAOB", "AICPA", "auditing standards", "responsibilities principle",
      "performance principle", "reporting principle"]),

    (3,  date(2026, 1, 20), "Planning & Materiality",
     ["planning stage", "engagement letter", "materiality", "tolerable misstatement",
      "preliminary analytical procedures", "client acceptance"]),

    (4,  date(2026, 1, 22), "Risk Assessment & Fraud",
     ["inherent risk", "control risk", "detection risk", "audit risk model",
      "risk of material misstatement", "fraud vs error", "misappropriation of assets",
      "fraudulent financial reporting", "revenue as presumed fraud risk"]),

    (5,  date(2026, 1, 27), "Risk Assessment",
     ["audit risk model", "substantive procedures", "risk-based approach",
      "financial statement assertions", "analytical procedures in planning",
      "Coca-Cola case"]),

    (6,  date(2026, 1, 29), "Quiz 1 / Pam Beasley Case",
     ["Pam Beasley case", "quiz review", "predecessor auditor inquiries",
      "client acceptance procedures"]),

    (7,  date(2026, 2, 3), "Internal Control Environment",
     ["COSO framework", "control environment", "entity-level controls",
      "tone at the top", "segregation of duties"]),

    (8,  date(2026, 2, 5), "Internal Controls",
     ["preventive controls", "detective controls", "manual controls",
      "IT-dependent controls", "application controls", "IT general controls",
      "control deficiencies", "material weakness", "significant deficiency"]),

    (9,  date(2026, 2, 10), "Internal Controls — Testing",
     ["test of design", "test of operating effectiveness", "walkthroughs",
      "inquiry observation inspection reperformance", "PCAOB AS 2201",
      "precision of controls", "level of aggregation", "frequency of controls"]),

    (10, date(2026, 2, 12), "Internal Controls — Freeman Manufacturing",
     ["Freeman Manufacturing case", "control testing documentation",
      "management review controls", "MRC precision", "criteria for investigation"]),

    (11, date(2026, 2, 17), "Internal Controls — Project Work",
     ["internal controls project", "MRC design", "MRC operating effectiveness"]),

    (12, date(2026, 2, 19), "Internal Controls — Wrap-up",
     ["internal controls conclusion", "MRC BDO framework",
      "Deer Tracks case", "revenue forecast controls", "goodwill valuation assertion"]),

    (13, date(2026, 2, 24), "Audit Procedures & Evidence",
     ["nature of audit evidence", "sufficiency and appropriateness",
      "audit procedures: inquiry observation inspection reperformance",
      "confirmations", "external confirmations", "existence vs completeness",
      "direction of testing", "credit memos", "cutoff testing"]),

    (14, date(2026, 2, 26), "Test 1", []),

    (15, date(2026, 3, 3), "Substantive Procedures 1",
     ["substantive testing", "tests of details", "substantive analytical procedures",
      "accounts receivable", "revenue recognition", "shipping cutoff",
      "existence assertion", "valuation assertion"]),

    (16, date(2026, 3, 5), "Substantive Procedures 2",
     ["Apollo Shoes case", "inventory testing", "document review",
      "completeness assertion", "liability testing", "year-end cutoff"]),

    (17, date(2026, 3, 17), "Substantive Procedures 3",
     ["Pennington Technologies case", "going concern",
      "substantive procedures for estimates", "fair value measurements"]),

    (18, date(2026, 3, 19), "Substantive Procedures 4",
     ["subsequent events", "representation letters", "management representations",
      "audit adjustments", "waived adjustments"]),

    (19, date(2026, 3, 24), "Judgment Framework",
     ["KPMG professional judgment framework", "professional skepticism",
      "evaluating evidence", "contrary evidence", "auditor bias",
      "professional judgment steps"]),

    (20, date(2026, 3, 26), "Substantive Testing & Sampling Intro",
     ["auditing estimates", "three approaches to testing estimates",
      "independent calculation", "subsequent events approach",
      "management's process review", "always test data", "contrary evidence"]),

    (21, date(2026, 3, 31), "Sampling — Fundamentals",
     ["audit sampling", "statistical vs nonstatistical sampling",
      "sampling risk", "nonsampling risk", "tolerable misstatement",
      "expected misstatement", "sampling population"]),

    (22, date(2026, 4, 2), "Sampling — Application",
     ["attribute sampling", "variables sampling", "deviation rate",
      "tolerable deviation rate", "sample size factors",
      "projecting misstatements", "evaluating sample results"]),

    (23, date(2026, 4, 7), "Ethics",
     ["auditor independence", "AICPA Code of Professional Conduct",
      "threats to independence", "safeguards", "conflicts of interest",
      "objectivity", "integrity"]),

    (24, date(2026, 4, 9), "Test 2", []),

    (25, date(2026, 4, 14), "Completing the Audit",
     ["subsequent events", "Type 1 and Type 2 subsequent events",
      "going concern evaluation", "management representation letter",
      "final analytical procedures", "engagement quality review"]),

    (26, date(2026, 4, 16), "Completing the Audit — Wrap-up",
     ["audit documentation", "working papers", "archiving",
      "audit committee communication", "significant deficiencies",
      "material weaknesses", "fraud findings"]),

    (27, date(2026, 4, 21), "Reporting",
     ["audit opinion types", "unmodified opinion", "qualified opinion",
      "adverse opinion", "disclaimer of opinion", "emphasis of matter",
      "audit report components", "basis for opinion paragraph"]),

    (28, date(2026, 4, 23), "Subsequently Discovered Facts",
     ["subsequently discovered facts", "omitted procedures",
      "Consequences of a Cover-up case", "auditor obligations post-report",
      "dual dating"]),

    (29, date(2026, 4, 28), "Current Events & Review",
     ["current events in auditing", "comprehensive review",
      "judgment and skepticism", "exam preparation"]),
]

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def get_completed_classes(as_of: date = None) -> list[tuple]:
    """Return classes that have been completed as of the given date."""
    if as_of is None:
        as_of = date.today()
    return [(num, d, topic, concepts)
            for num, d, topic, concepts in SCHEDULE
            if d <= as_of and concepts]  # skip empty (test days)


def get_weighted_topics(as_of: date = None, num_questions: int = 10) -> dict:
    """
    Return a dict with:
      - 'topic_plan': list of {topic, concepts, weight, num_questions, recency_label}
      - 'summary': human-readable explanation of what's being tested and why
      - 'all_concepts': flat list of all concepts to include in the prompt
    """
    if as_of is None:
        as_of = date.today()

    completed = get_completed_classes(as_of)
    if not completed:
        return {"topic_plan": [], "summary": "No classes completed yet.", "all_concepts": []}

    # Assign weights by recency (index from end = how long ago)
    n = len(completed)
    weighted = []
    for i, (num, d, topic, concepts) in enumerate(completed):
        classes_ago = n - 1 - i  # 0 = most recent
        if classes_ago <= 1:
            weight = 4      # HIGH — just covered
            label = "🔴 Recent (high priority)"
        elif classes_ago <= 5:
            weight = 3      # MEDIUM — solidifying
            label = "🟡 Moderate (solidifying)"
        elif classes_ago <= 13:
            weight = 2      # LOW — spaced review
            label = "🟢 Older (spaced review)"
        else:
            weight = 1      # REVIEW — long-term retention
            label = "🔵 Early material (retention check)"
        weighted.append({
            "class_num": num,
            "date": d.strftime("%b %d"),
            "topic": topic,
            "concepts": concepts,
            "weight": weight,
            "label": label,
        })

    total_weight = sum(w["weight"] for w in weighted)

    # Allocate questions proportionally, minimum 1 per recent topic
    for entry in weighted:
        raw = round(entry["weight"] / total_weight * num_questions)
        entry["num_questions"] = max(1, raw)

    # Trim to exact total (add/remove from lowest-priority topics)
    allocated = sum(e["num_questions"] for e in weighted)
    diff = allocated - num_questions
    # Adjust from the lowest-weight entries first
    sorted_by_weight = sorted(weighted, key=lambda x: x["weight"])
    for entry in sorted_by_weight:
        if diff == 0:
            break
        if diff > 0 and entry["num_questions"] > 1:
            entry["num_questions"] -= 1
            diff -= 1
        elif diff < 0:
            entry["num_questions"] += 1
            diff += 1

    all_concepts = []
    for entry in weighted:
        all_concepts.extend(entry["concepts"])

    # Build human-readable summary
    recent = [e for e in weighted if e["weight"] >= 3]
    summary_lines = [
        f"**{len(completed)} classes covered** through today ({as_of.strftime('%b %d')}).",
        "",
        "Questions are weighted by recency using spaced repetition:",
    ]
    for entry in reversed(weighted[-5:]):  # show last 5 classes
        summary_lines.append(
            f"- Class {entry['class_num']} ({entry['date']}): **{entry['topic']}** "
            f"— {entry['num_questions']} question(s) {entry['label']}"
        )
    if len(weighted) > 5:
        older_q = sum(e["num_questions"] for e in weighted[:-5])
        summary_lines.append(f"- Earlier classes: **{older_q} question(s)** for long-term retention")

    return {
        "topic_plan": weighted,
        "summary": "\n".join(summary_lines),
        "all_concepts": all_concepts,
    }


def get_upcoming_exam(as_of: date = None) -> tuple | None:
    """Return the next exam/test/quiz date after today."""
    if as_of is None:
        as_of = date.today()
    exams = [(num, d, topic) for num, d, topic, _ in SCHEDULE
             if d > as_of and ("Test" in topic or "Quiz" in topic or "Final" in topic or "Exam" in topic)]
    return exams[0] if exams else None


def days_until_next_exam(as_of: date = None) -> int | None:
    exam = get_upcoming_exam(as_of)
    if not exam:
        return None
    return (exam[1] - (as_of or date.today())).days


def get_weighted_topics_with_performance(progress: dict, all_cards: list,
                                         num_questions: int = 10,
                                         as_of: date = None) -> dict:
    """
    Combined topic weighting: recency × inverse-performance.

    Algorithm:
      combined_weight = recency_weight × performance_multiplier

    Performance multipliers (based on SM-2 accuracy per topic):
      < 40%  → 2.0×   (struggling — urgent reinforcement)
      40-60% → 1.5×   (below target)
      60-80% → 1.0×   (on track)
      ≥ 80%  → 0.7×   (strong — still needs spaced review)
      no data→ 1.2×   (unseen — slight priority boost)

    This ensures recent material you're weak at rises to the top,
    while strong material from long ago naturally fades in frequency.
    """
    base = get_weighted_topics(as_of, num_questions)
    if not base["topic_plan"]:
        return base

    # Build topic accuracy map from SM-2 history
    from progress import get_weak_spots
    weak_list = get_weak_spots(progress, all_cards) if all_cards else []
    accuracy_map = {w["topic"]: w["accuracy"] for w in weak_list}

    for entry in base["topic_plan"]:
        acc = accuracy_map.get(entry["topic"])
        if acc is None:
            mult, perf_label = 1.2, "New"
        elif acc < 0.40:
            mult, perf_label = 2.0, f"{int(acc*100)}% — needs work"
        elif acc < 0.60:
            mult, perf_label = 1.5, f"{int(acc*100)}% — below target"
        elif acc < 0.80:
            mult, perf_label = 1.0, f"{int(acc*100)}% — on track"
        else:
            mult, perf_label = 0.7, f"{int(acc*100)}% — strong"

        entry["accuracy"]       = acc
        entry["perf_label"]     = perf_label
        entry["combined_weight"] = round(entry["weight"] * mult, 2)

    # Re-allocate question counts by combined weight
    total_w = sum(e["combined_weight"] for e in base["topic_plan"]) or 1
    for entry in base["topic_plan"]:
        entry["num_questions"] = max(1, round(entry["combined_weight"] / total_w * num_questions))

    # Trim to exact total
    diff = sum(e["num_questions"] for e in base["topic_plan"]) - num_questions
    for entry in sorted(base["topic_plan"], key=lambda x: x["combined_weight"]):
        if diff == 0: break
        if diff > 0 and entry["num_questions"] > 1:
            entry["num_questions"] -= 1; diff -= 1
        elif diff < 0:
            entry["num_questions"] += 1; diff += 1

    # Build focus summary for the dashboard
    top3 = sorted(base["topic_plan"], key=lambda x: x["combined_weight"], reverse=True)[:3]
    base["focus_summary"] = " · ".join(
        f"{e['topic']} ({e['perf_label']})" for e in top3
    )
    base["top_topics"] = top3
    return base
