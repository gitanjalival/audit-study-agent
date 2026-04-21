"""
app.py — Audit Study Agent · ACCT 40510 · Notre Dame · Spring 2026

Evidence-based study companion: spaced repetition (SM-2), retrieval practice,
confidence-based learning, and immediate feedback.
"""

import html as _html
import json
import os
import threading
import time
from datetime import date

import streamlit as st

from agent import generate_summary, generate_study_plan, generate_practice_questions
from flashcards import generate_flashcards, get_due_cards, count_due, load_flashcards, save_flashcards
from progress import (load_progress, save_progress, record_review, get_today_stats,
                      get_weak_spots, streak_calendar, add_xp, get_xp_today,
                      check_new_achievements, DAILY_GOAL_XP, XP_FOR_RATING, ACHIEVEMENTS)
from schedule import get_weighted_topics

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Audit Study Agent",
    page_icon="",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CACHE_FILE = os.path.join(os.path.dirname(__file__), "materials_cache.json")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=DM+Serif+Display:ital@0;1&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }

.stApp { background: #F7F5F1; min-height: 100vh; }
.main .block-container { padding: 2rem 1.75rem 5rem 1.75rem; max-width: 720px; }

/* ── Header ── */
.app-header {
    text-align: center;
    padding: 32px 0 24px;
    border-bottom: 1px solid #E8E4DC;
    margin-bottom: 28px;
}
.app-eyebrow {
    font-size: 0.65rem; letter-spacing: 0.18em; text-transform: uppercase;
    color: #B0ADA6; font-weight: 500; margin: 0 0 10px 0;
}
.app-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2.1rem; font-weight: 400; color: #1E1D1A;
    letter-spacing: -0.01em; margin: 0; line-height: 1.15;
}
.app-title em { font-style: italic; color: #B87C65; }

/* ── API banner ── */
.api-banner {
    background: #FFFFFF; border: 1px solid #E8E4DC;
    border-radius: 18px; padding: 22px 26px; margin-bottom: 24px;
}
.api-banner-text { font-size: 0.88rem; color: #5C5A54; line-height: 1.65; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #EDEBE6; border-radius: 12px; padding: 4px; gap: 2px;
    margin-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px; padding: 9px 18px; font-weight: 500; font-size: 0.8rem;
    color: #A8A49C; border: none !important; background: transparent;
    letter-spacing: 0.01em;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important; color: #1E1D1A !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08); font-weight: 600 !important;
}

/* ── Section label ── */
.section-label {
    font-size: 0.62rem; font-weight: 700; color: #B0ADA6;
    text-transform: uppercase; letter-spacing: 0.14em; margin: 24px 0 12px 0;
}

/* ── Stat tiles ── */
.stat-tile {
    background: #FFFFFF; border-radius: 16px; padding: 20px 10px 16px; text-align: center;
    border: 1px solid #E8E4DC; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.stat-value {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem; font-weight: 400; color: #1E1D1A; line-height: 1; margin-bottom: 8px;
}
.stat-label { font-size: 0.6rem; color: #B0ADA6; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600; }

/* ── Start / complete cards ── */
.hero-card {
    background: #FFFFFF; border-radius: 20px; padding: 52px 44px;
    border: 1px solid #E8E4DC;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 12px 40px -8px rgba(0,0,0,0.07);
    text-align: center; margin: 8px 0 20px 0;
}
.hero-rule { width: 36px; height: 2px; background: #B87C65; border-radius: 2px; margin: 0 auto 24px; }
.hero-eyebrow {
    font-size: 0.62rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: #B0ADA6; font-weight: 600; margin-bottom: 12px;
}
.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.6rem; font-weight: 400; color: #1E1D1A; margin: 0 0 10px 0; line-height: 1.2;
}
.hero-body { font-size: 0.87rem; color: #8A8780; margin: 0 0 30px 0; line-height: 1.7; max-width: 360px; margin-left: auto; margin-right: auto; }
.chip-row { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-bottom: 30px; }
.chip {
    padding: 5px 14px; border-radius: 100px;
    font-size: 0.67rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
}
.chip-accent { background: #F2EAE5; color: #B87C65; }
.chip-sage   { background: #EDF3EF; color: #7A9E88; }
.chip-neutral { background: #EDEBE6; color: #5C5A54; }

/* ── Caught-up card ── */
.caught-card {
    background: #EDF3EF; border: 1px solid #BDD3C5; border-radius: 20px;
    padding: 52px 44px; text-align: center; margin: 8px 0 20px 0;
}
.caught-eyebrow {
    font-size: 0.62rem; letter-spacing: 0.16em; text-transform: uppercase;
    color: #5A8068; font-weight: 600; margin-bottom: 12px;
}
.caught-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem; font-weight: 400; color: #2A4A33; margin: 0 0 10px 0;
}
.caught-body { font-size: 0.87rem; color: #4A7056; margin: 0 0 30px 0; line-height: 1.7; }

/* ── Flip card ── */
.flip-card {
    background: #FFFFFF; border-radius: 20px;
    border: 1px solid #E8E4DC;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 12px 40px -8px rgba(0,0,0,0.07);
    padding: 54px 52px 46px; text-align: center; min-height: 280px;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    margin: 6px 0 20px 0; position: relative; overflow: hidden;
}
.flip-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: #B87C65;
}
.card-topic-pill {
    background: #F2EAE5; color: #B87C65; padding: 4px 13px; border-radius: 100px;
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    margin-bottom: 22px; display: inline-block;
}
.card-q-label {
    font-size: 0.6rem; color: #D0CCC4; text-transform: uppercase;
    letter-spacing: 0.14em; font-weight: 700; margin-bottom: 10px;
}
.card-question { font-size: 1.18rem; color: #1E1D1A; line-height: 1.75; font-weight: 500; max-width: 500px; }
.card-divider  { width: 32px; height: 1px; background: #E8E4DC; margin: 20px auto; }
.card-answer   { font-size: 0.96rem; color: #5C5A54; line-height: 1.85; max-width: 520px; font-weight: 400; }
.card-question-ghost { font-size: 0.8rem; color: #A8A49C; max-width: 480px; line-height: 1.6; font-weight: 400; margin-bottom: 4px; }

/* ── Progress bar ── */
.progress-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px; }
.progress-count { font-size: 0.7rem; color: #B0ADA6; font-weight: 500; }
.progress-track { background: #E8E4DC; border-radius: 100px; height: 4px; margin-bottom: 18px; }
.progress-fill  { background: #B87C65; border-radius: 100px; height: 4px; }
.rating-hint { text-align: center; font-size: 0.72rem; color: #B0ADA6; font-weight: 400; margin: 8px 0 12px; letter-spacing: 0.01em; }

/* ── Streak strip ── */
.streak-wrap { background: #FFFFFF; border: 1px solid #E8E4DC; border-radius: 16px; padding: 18px 20px; margin-bottom: 12px; }
.streak-strip { display: flex; gap: 6px; justify-content: space-between; }
.day-item { display: flex; flex-direction: column; align-items: center; gap: 5px; flex: 1; }
.day-name { font-size: 0.57rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; color: #B0ADA6; }
.day-dot  { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
.day-on   { background: #B87C65; }
.day-off  { background: #E8E4DC; }
.day-today { box-shadow: 0 0 0 2px #B87C65, 0 0 0 4px rgba(184,124,101,0.18); }
.day-check { font-size: 0.65rem; color: #FFFFFF; font-weight: 700; }
.day-inner { width: 7px; height: 7px; border-radius: 50%; background: #C8C4BC; }

/* ── Weak spots ── */
.ws-card { background: #FFFFFF; border: 1px solid #E8E4DC; border-radius: 16px; padding: 20px 22px; }
.ws-row  { margin-bottom: 16px; }
.ws-row:last-child { margin-bottom: 0; }
.ws-header { display: flex; justify-content: space-between; font-size: 0.82rem; font-weight: 500; color: #2C2C28; margin-bottom: 7px; }
.ws-pct    { color: #8A8780; font-weight: 400; }
.ws-track  { background: #E8E4DC; border-radius: 100px; height: 7px; }
.ws-fill   { border-radius: 100px; height: 7px; }

/* ── Buttons ── */
.stButton > button {
    border-radius: 10px !important; font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important; transition: all 0.15s ease !important;
    letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"] {
    background: #B87C65 !important; border: none !important; color: white !important;
    box-shadow: 0 2px 8px rgba(184,124,101,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #A86C57 !important;
    box-shadow: 0 4px 14px rgba(184,124,101,0.38) !important;
}
.stButton > button[kind="secondary"] {
    background: transparent !important; color: #5C5A54 !important;
    border: 1.5px solid #E8E4DC !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #B87C65 !important; color: #B87C65 !important;
}

/* ── Goal bar ── */
.goal-wrap { margin: 0 0 22px; }
.goal-row { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:5px; }
.goal-label { font-size:0.72rem; letter-spacing:0.09em; text-transform:uppercase; color:#B0ADA6; font-weight:500; }
.goal-value { font-size:0.72rem; font-weight:600; color:#B87C65; }
.goal-track { background:#E8E4DC; border-radius:99px; height:5px; }
.goal-fill  { background:linear-gradient(90deg,#B87C65,#D4956A); border-radius:99px; height:5px; }

/* ── Achievements ── */
.ach-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:12px 0 20px; }
.ach-card { background:#FFFFFF; border:1px solid #E8E4DC; border-radius:14px; padding:14px 16px; }
.ach-card.earned { border-color:#B87C65; background:#FDF9F7; }
.ach-card.locked { opacity:0.5; }
.ach-name { font-size:0.82rem; font-weight:600; color:#1E1D1A; margin:0 0 3px; }
.ach-desc { font-size:0.72rem; color:#8C8881; margin:0; }

/* ── Session complete XP banner ── */
.xp-banner {
    background:#FDF3EE; border:1px solid #F0D9CE; border-radius:18px;
    padding:24px; text-align:center; margin-bottom:16px;
}
.xp-number {
    font-family:'DM Serif Display',serif; font-size:2.8rem; color:#B87C65;
    line-height:1; margin:0 0 6px;
}
.xp-sub { font-size:0.82rem; color:#8C8881; margin:0; }

/* ── New achievement pop ── */
.new-ach-card {
    background:#FDF3EE; border:1.5px solid #B87C65; border-radius:14px;
    padding:14px 18px; margin-bottom:10px;
}
.new-ach-label { font-size:0.65rem; letter-spacing:0.12em; text-transform:uppercase; color:#B87C65; font-weight:600; margin:0 0 2px; }
.new-ach-name  { font-size:0.9rem; font-weight:700; color:#1E1D1A; margin:0 0 2px; }
.new-ach-desc  { font-size:0.75rem; color:#5C5A54; margin:0; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "materials":{}, "cache_date":None, "progress":None,
    "flash_queue":[], "flash_idx":0, "flash_flipped":False, "flash_correct":0,
    "flash_generating":False, "flash_gen_error":None,
    "session_xp":0, "session_ratings":[], "new_achievements":[],
    "last_summary":None, "last_plan":None,
    "api_key":"",
}.items():
    if k not in st.session_state: st.session_state[k] = v

# ─── Load materials ────────────────────────────────────────────────────────────
def _load_cache():
    if not os.path.exists(CACHE_FILE): return {}, None
    with open(CACHE_FILE) as f: data = json.load(f)
    return {n:m for n,m in data.get("files",{}).items() if m.get("text","").strip()}, data.get("fetched_at")

if not st.session_state.materials:
    mats, fetched = _load_cache()
    if mats:
        st.session_state.materials  = mats
        st.session_state.cache_date = fetched

if st.session_state.progress is None:
    st.session_state.progress = load_progress()

# ─── Resolve API key ───────────────────────────────────────────────────────────
api_key = ""
try:    api_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    api_key = os.environ.get("ANTHROPIC_API_KEY","") or st.session_state.api_key

# ─── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="app-header">'
    '<p class="app-eyebrow">ACCT 40510 · Notre Dame · Spring 2026</p>'
    '<h1 class="app-title">Audit Study <em>Agent</em></h1>'
    '</div>',
    unsafe_allow_html=True,
)

# ─── Daily goal bar (always visible) ──────────────────────────────────────────
def _goal_bar(progress):
    xp    = get_xp_today(progress)
    pct   = min(100, int(xp / DAILY_GOAL_XP * 100))
    label = "Goal reached!" if xp >= DAILY_GOAL_XP else f"{xp} / {DAILY_GOAL_XP} XP today"
    return (
        f'<div class="goal-wrap">'
        f'<div class="goal-row"><span class="goal-label">Daily goal</span>'
        f'<span class="goal-value">{label}</span></div>'
        f'<div class="goal-track"><div class="goal-fill" style="width:{pct}%"></div></div>'
        f'</div>'
    )

st.markdown(_goal_bar(st.session_state.progress), unsafe_allow_html=True)

# ─── API key — soft notice only (flashcards work without it) ───────────────────
# No hard gate. API key is only required for AI Tools tab features.

# ─── Helpers ───────────────────────────────────────────────────────────────────
def _text(d):
    return "\n\n---\n\n".join(f"[FILE: {n}]\n{m['text']}" for n,m in d.items() if m.get("text","").strip())

def _acc_color(a):
    if a < 0.5:  return "#C46356"   # dusty red
    if a < 0.7:  return "#C4963A"   # warm amber
    if a < 0.85: return "#7A9E88"   # sage green
    return "#B87C65"                # terracotta

# ─── Background flashcard generation ──────────────────────────────────────────
def _bg_generate(api_key_val, materials_text, topic_plan):
    """Run in a daemon thread — writes cards to disk when done."""
    try:
        cards = generate_flashcards(api_key_val, materials_text, topic_plan)
        save_flashcards(cards)
    except Exception as e:
        # Write error to a small sentinel file the main thread can detect
        try:
            err_path = os.path.join(os.path.dirname(__file__), "_flash_gen_error.txt")
            with open(err_path, "w") as f:
                f.write(str(e))
        except Exception:
            pass

def _start_bg_generation(api_key_val, mats_dict):
    """Kick off background generation if not already running."""
    if st.session_state.flash_generating:
        return
    # Clear any previous error sentinel
    err_path = os.path.join(os.path.dirname(__file__), "_flash_gen_error.txt")
    if os.path.exists(err_path):
        os.remove(err_path)
    st.session_state.flash_generating = True
    st.session_state.flash_gen_error  = None
    w = get_weighted_topics(num_questions=50)
    if mats_dict:
        notes = {k:v for k,v in mats_dict.items() if v.get("type") in ("notes","reading")}
        mat_text = _text(notes) if notes else _text(mats_dict)
    else:
        mat_text = ""
    t = threading.Thread(target=_bg_generate, args=(api_key_val, mat_text, w["topic_plan"]), daemon=True)
    t.start()

def _streak_strip(progress, n=7):
    cal = streak_calendar(progress, n)
    today_str = date.today().isoformat()
    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    html = '<div class="streak-wrap"><div class="streak-strip">'
    for i, d in enumerate(cal):
        is_today = d["date"] == today_str
        dot_cls  = ("day-on" if d["studied"] else "day-off") + (" day-today" if is_today else "")
        inner    = '<span class="day-check">✓</span>' if d["studied"] else '<div class="day-inner"></div>'
        # derive weekday name from date string
        try:
            from datetime import datetime as _dt
            wd = _dt.strptime(d["date"], "%Y-%m-%d").strftime("%a")
        except Exception:
            wd = day_names[i % 7]
        html += f'<div class="day-item"><span class="day-name">{wd}</span><div class="day-dot {dot_cls}">{inner}</div></div>'
    html += '</div></div>'
    return html

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Settings")
    mats = st.session_state.materials
    if mats:
        st.success(f"{len(mats)} files loaded")
    else:
        st.warning("No materials loaded yet")
    if st.session_state.cache_date: st.caption(f"Updated: {st.session_state.cache_date}")
    st.divider()
    st.caption("Materials auto-refresh from Box after each Tue/Thu class.")
    st.divider()
    st.divider()
    st.caption("API key — needed for AI tools & flashcard regeneration only.")
    key_input = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-…", value=api_key or "")
    if key_input and key_input != api_key:
        st.session_state.api_key = key_input
        api_key = key_input
        st.rerun()
    if api_key:
        st.success("Key saved")
    st.divider()
    if st.button("Regenerate flashcards"):
        if not api_key:
            st.error("Enter an API key above first.")
        else:
            with st.spinner("Generating…"):
                try:
                    w = get_weighted_topics(num_questions=50)
                    if mats:
                        notes = {k:v for k,v in mats.items() if v.get("type") in ("notes","reading")}
                        materials_text = _text(notes) if notes else _text(mats)
                    else:
                        materials_text = ""
                    cards = generate_flashcards(api_key, materials_text, w["topic_plan"])
                    save_flashcards(cards)
                    st.session_state.flash_queue = []
                    st.success(f"{len(cards)} cards ready")
                    st.rerun()
                except Exception as e: st.error(str(e))

    st.divider()
    with st.expander("AI Tools"):
        if not mats:
            st.caption("Materials will auto-sync after class.")
        elif not api_key:
            st.caption("Enter API key above to use AI tools.")
        else:
            tool = st.radio("", ["Summary", "Study Plan"], horizontal=True, label_visibility="collapsed")
            if tool == "Summary":
                if st.button("Generate summary", type="primary", key="sb_sum"):
                    with st.spinner("Summarizing…"):
                        notes_only = {k:v for k,v in mats.items() if v.get("type") in ("notes","reading")}
                        st.session_state.last_summary = generate_summary(api_key, _text(notes_only or mats))
                if st.session_state.last_summary:
                    st.markdown(st.session_state.last_summary)
                    st.download_button("Download", st.session_state.last_summary, f"summary_{date.today()}.md", "text/markdown")
            else:
                nc   = st.date_input("Next class", value=date.today(), key="sb_nc")
                exam = st.date_input("Exam date", key="sb_exam")
                hrs  = st.slider("Hours/day", 0.5, 4.0, 1.5, 0.5, key="sb_hrs")
                if st.button("Generate study plan", type="primary", key="sb_plan"):
                    with st.spinner("Building plan…"):
                        st.session_state.last_plan = generate_study_plan(api_key, _text(mats), str(nc), str(exam), hrs, "")
                if st.session_state.last_plan:
                    st.markdown(st.session_state.last_plan)
                    st.download_button("Download", st.session_state.last_plan, f"plan_{date.today()}.md", "text/markdown")

# ─── Auto-generate flashcards in background on load ───────────────────────────
mats = st.session_state.materials
_existing_cards = load_flashcards()
_err_path = os.path.join(os.path.dirname(__file__), "_flash_gen_error.txt")

if not _existing_cards and api_key and not st.session_state.flash_generating:
    _start_bg_generation(api_key, mats)

# Check if background thread just finished (file appeared) or errored
if st.session_state.flash_generating:
    if load_flashcards():                       # cards file now has content
        st.session_state.flash_generating = False
        st.rerun()
    elif os.path.exists(_err_path):             # error sentinel written
        with open(_err_path) as _f:
            st.session_state.flash_gen_error = _f.read()
        st.session_state.flash_generating = False
        os.remove(_err_path)

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_flash, tab_progress = st.tabs(["Study", "Progress"])
mats = st.session_state.materials

# ════════════════════════════════════════════ FLASHCARDS ═════════════════════
with tab_flash:
    progress  = st.session_state.progress
    all_cards = load_flashcards()

    # ── No cards yet — show loading state or error ────────────────────────────
    if not all_cards:
        if st.session_state.flash_gen_error:
            st.error(f"Could not generate flashcards: {st.session_state.flash_gen_error}")
            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Try again", use_container_width=True, type="primary"):
                    st.session_state.flash_gen_error = None
                    _start_bg_generation(api_key, mats)
                    st.rerun()
        elif st.session_state.flash_generating:
            st.markdown(
                '<div class="hero-card">'
                '<p class="hero-eyebrow">Building your deck</p>'
                '<h2 class="hero-title">Generating 50 cards…</h2>'
                '<p class="hero-body">AI is reading your course materials and creating cards weighted by what Prof. Morrison tests. This takes about 30 seconds — hang tight.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            time.sleep(3)
            st.rerun()
        else:
            # Shouldn't normally reach here, but offer manual trigger as fallback
            st.markdown(
                '<div class="hero-card">'
                '<p class="hero-eyebrow">Flashcard deck</p>'
                '<h2 class="hero-title">Ready to generate</h2>'
                '<p class="hero-body">Your deck will be built from your course materials and weighted by what Prof. Morrison tests.</p>'
                '</div>',
                unsafe_allow_html=True,
            )
            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Generate flashcards", use_container_width=True, type="primary"):
                    _start_bg_generation(api_key, mats)
                    st.rerun()

    # ── Dashboard — cards exist, no active session ────────────────────────────
    elif not st.session_state.flash_queue:
        stats  = get_today_stats(progress)
        counts = count_due(all_cards, progress)
        total  = counts["due"] + counts["new"]

        # Stat row
        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["streak"]}</div><div class="stat-label">Day streak</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["cards_today"]}</div><div class="stat-label">Today</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-tile"><div class="stat-value">{total}</div><div class="stat-label">Due</div></div>', unsafe_allow_html=True)

        # Streak calendar
        st.markdown(_streak_strip(progress, 7), unsafe_allow_html=True)

        if total > 0:
            st.markdown(
                f'<div class="hero-card" style="margin-top:12px">'
                f'<p class="hero-eyebrow">Ready to study</p>'
                f'<h2 class="hero-title">{total} cards due today</h2>'
                f'<p class="hero-body">{counts["due"]} reviews &nbsp;·&nbsp; {counts["new"]} new cards.<br>'
                f'Consistent daily sessions are the single biggest predictor of exam performance.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Begin session", use_container_width=True, type="primary"):
                    q = get_due_cards(all_cards, progress)
                    st.session_state.flash_queue     = q
                    st.session_state.flash_idx       = 0
                    st.session_state.flash_flipped   = False
                    st.session_state.flash_correct   = 0
                    st.session_state.session_xp      = 0
                    st.session_state.session_ratings = []
                    st.rerun()
        else:
            st.markdown(
                '<div class="caught-card">'
                '<p class="caught-eyebrow">All caught up</p>'
                '<h2 class="caught-title">Nothing due today</h2>'
                '<p class="caught-body">Your spaced repetition schedule is clear. Check back tomorrow — consistency compounds.</p>'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Active session ────────────────────────────────────────────────────────
    else:
        queue   = st.session_state.flash_queue
        idx     = st.session_state.flash_idx
        flipped = st.session_state.flash_flipped

        # Session complete
        if idx >= len(queue):
            # Check for new achievements
            prog = st.session_state.progress
            new_ach = check_new_achievements(prog, st.session_state.session_ratings)
            if new_ach:
                prog["achievements"] = list(set(prog.get("achievements", [])) | set(new_ach))
                st.session_state.progress = prog
                save_progress(prog)

            sess_xp  = st.session_state.session_xp
            xp_today = get_xp_today(prog)
            goal_hit = xp_today >= DAILY_GOAL_XP

            # XP banner
            st.markdown(
                f'<div class="xp-banner">'
                f'<div class="xp-number">+{sess_xp}</div>'
                f'<p class="xp-sub">XP earned this session</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Goal reached callout
            if goal_hit:
                st.markdown(
                    '<div class="caught-card" style="margin-bottom:12px">'
                    '<p class="caught-eyebrow">Daily goal</p>'
                    '<h2 class="caught-title" style="font-size:1.3rem">Goal reached!</h2>'
                    f'<p class="caught-body">{xp_today} XP today — you\'re done for the day. See you tomorrow.</p>'
                    '</div>',
                    unsafe_allow_html=True,
                )

            # New achievements
            if new_ach:
                st.markdown('<p class="section-label">New achievements</p>', unsafe_allow_html=True)
                for aid in new_ach:
                    a = ACHIEVEMENTS.get(aid, {})
                    st.markdown(
                        f'<div class="new-ach-card">'
                        f'<p class="new-ach-label">Achievement unlocked</p>'
                        f'<p class="new-ach-name">{a.get("name","")}</p>'
                        f'<p class="new-ach-desc">{a.get("desc","")}</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            # Stats chips
            correct = st.session_state.flash_correct
            total   = len(queue)
            pct     = int(correct / total * 100) if total else 0
            st.markdown(
                f'<div class="chip-row" style="margin-bottom:20px">'
                f'<span class="chip chip-sage">Streak: {get_today_stats(prog)["streak"]} days</span>'
                f'<span class="chip chip-neutral">{correct}/{total} correct · {pct}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Back to dashboard", use_container_width=True, type="primary"):
                    st.session_state.flash_queue    = []
                    st.session_state.flash_idx      = 0
                    st.session_state.session_xp     = 0
                    st.session_state.session_ratings = []
                    st.rerun()

        # Active card
        else:
            card = queue[idx]
            pct  = idx / len(queue) * 100

            st.markdown(
                f'<div class="progress-row">'
                f'<span class="progress-count">Card {idx+1} of {len(queue)}</span>'
                f'<span class="progress-count">{int(pct)}%</span>'
                f'</div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.1f}%"></div></div>',
                unsafe_allow_html=True,
            )

            fh = _html.escape(card.get("front",""))
            bh = _html.escape(card.get("back",""))
            th = _html.escape(card.get("topic",""))

            if not flipped:
                st.markdown(
                    f'<div class="flip-card">'
                    f'<span class="card-topic-pill">{th}</span>'
                    f'<p class="card-q-label">Question</p>'
                    f'<p class="card-question">{fh}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                col = st.columns([1,2,1])[1]
                with col:
                    if st.button("Reveal answer", use_container_width=True, type="primary"):
                        st.session_state.flash_flipped = True
                        st.rerun()
            else:
                st.markdown(
                    f'<div class="flip-card">'
                    f'<span class="card-topic-pill">{th}</span>'
                    f'<p class="card-q-label">Question</p>'
                    f'<p class="card-question-ghost">{fh}</p>'
                    f'<div class="card-divider"></div>'
                    f'<p class="card-q-label">Answer</p>'
                    f'<p class="card-answer">{bh}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<p class="rating-hint">How well did you know this?</p>', unsafe_allow_html=True)

                def _rate(r):
                    prog = st.session_state.progress
                    prog = record_review(prog, card["id"], r)
                    xp   = XP_FOR_RATING.get(r, 0)
                    prog = add_xp(prog, xp)
                    st.session_state.progress = prog
                    save_progress(prog)
                    if r >= 3: st.session_state.flash_correct += 1
                    st.session_state.session_xp      += xp
                    st.session_state.session_ratings.append(r)
                    st.session_state.flash_idx        += 1
                    st.session_state.flash_flipped     = False
                    st.rerun()

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("Again\nForgot it",   use_container_width=True, help="Forgot — shows again soon"): _rate(1)
                with c2:
                    if st.button("Hard\nStruggled",    use_container_width=True, help="Got it but struggled"):      _rate(2)
                with c3:
                    if st.button("Good\nKnew it",      use_container_width=True, help="Knew it well"):              _rate(3)
                with c4:
                    if st.button("Easy\nToo easy",     use_container_width=True, help="Way too easy"):              _rate(4)

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("End session", key="end_sess", type="secondary"):
                    st.session_state.flash_queue   = []
                    st.session_state.flash_idx     = 0
                    st.session_state.flash_flipped = False
                    st.rerun()

# ════════════════════════════════════════════ PRACTICE ═══════════════════════
with tab_quiz:
    if not mats:
        st.markdown(
            '<div class="hero-card">'
            '<p class="hero-eyebrow">Practice questions</p>'
            '<h2 class="hero-title">No materials yet</h2>'
            '<p class="hero-body">Your Box materials will auto-sync after class. In the meantime, use the Flashcards tab — it works right now.</p>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        notes_files = [k for k,v in mats.items() if v.get("type") in ("notes","reading")]
        quiz_files  = [k for k,v in mats.items() if v.get("type")=="quiz"]

        if not st.session_state.last_questions:
            c1, c2 = st.columns(2)
            with c1:
                num_q      = st.slider("Number of questions", 3, 15, 5, key="q_num")
                q_types    = st.multiselect("Question types", ["Multiple Choice","Short Answer","True/False"], default=["Multiple Choice","Short Answer"], key="q_types")
                difficulty = st.select_slider("Difficulty", ["Easy","Medium","Hard","Mixed"], value="Mixed", key="q_diff")
            with c2:
                st.markdown("**Topics — auto-selected by weight**")
                weighted   = get_weighted_topics(num_questions=num_q)
                st.info(weighted["summary"])

            if st.button("Generate questions", type="primary", key="btn_q"):
              if not api_key:
                st.warning("Add your Anthropic API key in the sidebar to generate questions.")
              else:
                with st.spinner("Crafting questions…"):
                    try:
                        w = get_weighted_topics(num_questions=num_q)
                        result = generate_practice_questions(
                            api_key=api_key,
                            notes_text=_text({k:mats[k] for k in notes_files}),
                            quiz_examples=_text({k:mats[k] for k in quiz_files}),
                            num_questions=num_q,
                            question_types=q_types,
                            difficulty=difficulty,
                            topic_plan=w["topic_plan"],
                        )
                        st.session_state.last_questions = result
                        st.session_state.quiz_answers   = {}
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_error     = None
                    except Exception as e:
                        st.session_state.quiz_error = str(e)

            if st.session_state.quiz_error:
                st.error(st.session_state.quiz_error)

        if st.session_state.last_questions:
            questions = st.session_state.last_questions
            submitted = st.session_state.quiz_submitted
            answers   = st.session_state.quiz_answers

            if st.button("New quiz", key="new_quiz"):
                st.session_state.last_questions = None
                st.session_state.quiz_submitted  = False
                st.rerun()

            st.divider()
            for i, q in enumerate(questions):
                qkey = f"q_{i}"
                st.markdown(f"**Q{i+1}. {q.get('question','')}**")
                if submitted:
                    ua = answers.get(qkey, "")
                    if q.get("type") in ("mc","true_false"):
                        ok = ua.strip().upper().startswith(q.get("correct","").strip().upper())
                        (st.success if ok else st.error)(f"{'Correct' if ok else 'Incorrect'}: {ua}")
                        if not ok: st.info(f"Correct answer: {q['correct']}")
                    else:
                        st.markdown(f"**Your answer:** {ua}" if ua.strip() else "_No answer_")
                        st.info(f"**Model answer:** {q['correct']}")
                    st.caption(f"Why: {q.get('explanation','')}")
                else:
                    if q.get("type") in ("mc","true_false"):
                        choice = st.radio(f"Q{i+1}", q.get("options",[]), index=None, key=qkey, label_visibility="collapsed")
                        answers[qkey] = choice or ""
                    else:
                        answers[qkey] = st.text_area(f"Q{i+1}", key=qkey, height=96, placeholder="Type your answer…", label_visibility="collapsed")
                st.divider()

            if not submitted:
                if st.button("Submit and grade", type="primary", key="submit_q"):
                    st.session_state.quiz_answers   = answers
                    st.session_state.quiz_submitted = True
                    st.rerun()
            else:
                gradeable = [q for q in questions if q.get("type") in ("mc","true_false")]
                if gradeable:
                    nc  = sum(1 for i,q in enumerate(questions) if q.get("type") in ("mc","true_false") and answers.get(f"q_{i}","").strip().upper().startswith(q.get("correct","").strip().upper()))
                    pct = int(nc / len(gradeable) * 100)
                    st.metric("Score", f"{nc}/{len(gradeable)}", f"{pct}%")
                md = f"# Quiz Results — {date.today()}\n\n" + "".join(
                    f"**Q{i+1}. {q['question']}**\n- Yours: {answers.get(f'q_{i}','')}\n- Correct: {q['correct']}\n- Why: {q['explanation']}\n\n"
                    for i,q in enumerate(questions)
                )
                st.download_button("Download results", md, f"quiz_{date.today()}.md", "text/markdown")

# ════════════════════════════════════════════ PROGRESS ═══════════════════════
with tab_progress:
    progress  = st.session_state.progress
    all_cards = load_flashcards()
    stats     = get_today_stats(progress)

    # Stat grid
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["streak"]}</div><div class="stat-label">Day streak</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["cards_today"]}</div><div class="stat-label">Today</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["longest_streak"]}</div><div class="stat-label">Best streak</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["total_reviews"]}</div><div class="stat-label">All time</div></div>', unsafe_allow_html=True)

    # Streak calendar
    st.markdown('<p class="section-label">Last 7 days</p>', unsafe_allow_html=True)
    st.markdown(_streak_strip(progress, 7), unsafe_allow_html=True)

    # Achievements
    st.markdown('<p class="section-label">Achievements</p>', unsafe_allow_html=True)
    earned_set = set(progress.get("achievements", []))
    cards_html = ""
    for aid, a in ACHIEVEMENTS.items():
        cls = "earned" if aid in earned_set else "locked"
        cards_html += (
            f'<div class="ach-card {cls}">'
            f'<p class="ach-name">{a["name"]}</p>'
            f'<p class="ach-desc">{a["desc"]}</p>'
            f'</div>'
        )
    st.markdown(f'<div class="ach-grid">{cards_html}</div>', unsafe_allow_html=True)

    # Weak spots
    if all_cards:
        weak = get_weak_spots(progress, all_cards)
        if weak:
            st.markdown('<p class="section-label">Weak spots — focus here first</p>', unsafe_allow_html=True)
            rows = ""
            for ws in weak[:8]:
                pct   = int(ws["accuracy"] * 100)
                color = _acc_color(ws["accuracy"])
                rows += (
                    f'<div class="ws-row">'
                    f'<div class="ws-header"><span>{ws["topic"]}</span><span class="ws-pct">{ws["correct"]}/{ws["total"]} · {pct}%</span></div>'
                    f'<div class="ws-track"><div class="ws-fill" style="width:{pct}%;background:{color}"></div></div>'
                    f'</div>'
                )
            st.markdown(f'<div class="ws-card">{rows}</div>', unsafe_allow_html=True)
        else:
            st.info("Study at least 3 cards per topic to see accuracy data here.")
    else:
        st.info("Generate flashcards to start tracking progress.")

    with st.expander("Reset all progress"):
        st.warning("Clears all streaks, XP, and review history. Cannot be undone.")
        if st.button("Reset progress", type="secondary"):
            from progress import _DEFAULTS
            st.session_state.progress = _DEFAULTS.copy()
            save_progress(st.session_state.progress)
            st.rerun()
