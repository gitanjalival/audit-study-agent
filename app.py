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
import streamlit.components.v1 as components

from agent import generate_summary, generate_study_plan, generate_practice_questions
from quiz import (load_questions, get_weighted_questions,
                  record_quiz_attempt, XP_CORRECT, XP_ATTEMPT)
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

/* ── Mode cards ── */
.mode-card {
    background: #FFFFFF; border: 1px solid #E8E4DC; border-radius: 18px;
    padding: 24px 20px 18px; text-align: left; height: 100%;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    margin-bottom: 12px;
}
.mode-card.active { border-color: #B87C65; background: #FDF9F7; }
.mode-eyebrow {
    font-size: 0.6rem; letter-spacing: 0.15em; text-transform: uppercase;
    color: #B87C65; font-weight: 700; margin: 0 0 8px 0;
}
.mode-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.15rem; font-weight: 400; color: #1E1D1A; margin: 0 0 8px 0;
}
.mode-body { font-size: 0.77rem; color: #8A8780; line-height: 1.6; margin: 0; }
.mode-divider { width: 28px; height: 2px; background: #B87C65; border-radius: 2px; margin: 0 0 14px 0; }

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
    # Practice session state
    "practice_queue":[], "practice_idx":0,
    "practice_selected":None, "practice_answered":False,
    "practice_correct":0, "practice_generating":False,
    "practice_mode":"spaced",
    # Legacy quiz tracking (kept for backward compat)
    "quiz_selected":None, "quiz_answered":False, "session_quiz_correct":0, "session_quiz_total":0,
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

def _confetti():
    """Burst of confetti on the parent page when a question is answered correctly."""
    components.html("""
<script>
(function() {
  var doc = window.parent.document;
  var canvas = doc.createElement('canvas');
  canvas.style.cssText = [
    'position:fixed','top:0','left:0','width:100%','height:100%',
    'pointer-events:none','z-index:99999','display:block'
  ].join(';');
  doc.body.appendChild(canvas);

  var W = window.parent.innerWidth;
  var H = window.parent.innerHeight;
  canvas.width  = W;
  canvas.height = H;
  var ctx = canvas.getContext('2d');

  var colors = [
    '#B87C65','#D4956A','#F7C59F',   // terracotta family
    '#7A9E88','#BDD3C5',             // sage
    '#F5D67B','#F2A65A',             // gold / amber
    '#C6A8D2','#85BCCF'             // lilac / sky
  ];

  var pieces = [];
  for (var i = 0; i < 120; i++) {
    pieces.push({
      x:    Math.random() * W,
      y:    Math.random() * H * -1,      // start above the viewport
      w:    Math.random() * 10 + 6,
      h:    Math.random() * 5  + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      rot:  Math.random() * Math.PI * 2,
      rotV: (Math.random() - 0.5) * 0.15,
      vx:   (Math.random() - 0.5) * 3,
      vy:   Math.random() * 4 + 3,
      opacity: 1
    });
  }

  var frame = 0;
  var FALL  = 90;   // frames of full fall
  var FADE  = 40;   // frames to fade out

  function draw() {
    ctx.clearRect(0, 0, W, H);
    frame++;
    var alive = false;
    pieces.forEach(function(p) {
      if (frame > FALL) {
        p.opacity = Math.max(0, 1 - (frame - FALL) / FADE);
      }
      if (p.opacity <= 0) return;
      alive = true;
      p.x  += p.vx;
      p.y  += p.vy;
      p.rot += p.rotV;
      ctx.save();
      ctx.globalAlpha = p.opacity;
      ctx.translate(p.x + p.w / 2, p.y + p.h / 2);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    });
    if (alive) requestAnimationFrame(draw);
    else        canvas.remove();
  }
  requestAnimationFrame(draw);
})();
</script>
""", height=0)

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
tab_practice, tab_flash, tab_progress = st.tabs(["Practice", "Review", "Progress"])
mats = st.session_state.materials

# ════════════════════════════════════════════ PRACTICE (PRIMARY) ═════════════
with tab_practice:
    progress  = st.session_state.progress
    all_cards = load_flashcards()

    # ── Helper: generate questions for a session ──────────────────────────────
    def _build_practice_questions(mode: str = "spaced"):
        """
        Generate 20 fresh MC questions from course materials.

        mode='week'   → questions drawn only from the last 1-2 classes
                         (weight 4 in the schedule; falls back to weight 3 if needed)
        mode='spaced' → full recency × inverse-performance algorithm across all topics
        """
        from schedule import get_weighted_topics_with_performance
        algo = get_weighted_topics_with_performance(progress, all_cards, num_questions=20)

        if mode == "week":
            # Filter to most recent topics (weight 4 = last 1-2 classes)
            plan = [e for e in algo["topic_plan"] if e.get("weight", 0) >= 4]
            if len(plan) < 2:            # fallback: include moderate-recency (weight 3)
                plan = [e for e in algo["topic_plan"] if e.get("weight", 0) >= 3]
            if not plan:                 # ultimate fallback: use everything
                plan = algo["topic_plan"]
            # Re-allocate all 20 questions among the selected recent topics
            tw = sum(e.get("combined_weight", e.get("weight", 1)) for e in plan) or 1
            for e in plan:
                e["num_questions"] = max(1, round(
                    e.get("combined_weight", e.get("weight", 1)) / tw * 20
                ))
            # Trim / pad to exactly 20
            diff = sum(e["num_questions"] for e in plan) - 20
            for e in sorted(plan, key=lambda x: x.get("combined_weight", 1)):
                if diff == 0: break
                if diff > 0 and e["num_questions"] > 1:
                    e["num_questions"] -= 1; diff -= 1
                elif diff < 0:
                    e["num_questions"] += 1; diff += 1
        else:
            plan = algo["topic_plan"]

        notes   = {k:v for k,v in mats.items() if v.get("type") in ("notes","reading")}
        quizzes = {k:v for k,v in mats.items() if v.get("type") == "quiz"}
        notes_t = _text(notes or mats)
        quiz_t  = _text(quizzes)
        raw_qs  = generate_practice_questions(
            api_key=api_key,
            notes_text=notes_t,
            quiz_examples=quiz_t,
            num_questions=20,
            question_types=["Multiple Choice"],
            difficulty="Mixed",
            topic_plan=plan,
        )
        # Normalise to questions_cache schema (add id, topic, class_num)
        out = []
        for i, q in enumerate(raw_qs):
            q.setdefault("id", f"live-{date.today().isoformat()}-{i}")
            q.setdefault("topic", "Auditing")
            q.setdefault("class_num", 0)
            q["_mode"] = mode          # tag so UI can show which mode is active
            # map options list to A/B/C/D if not already
            if q.get("options") and not q["options"][0].startswith("A"):
                labels = ["A","B","C","D"]
                q["options"] = [f"{labels[j]}. {o}" for j,o in enumerate(q["options"][:4])]
            out.append(q)
        return out

    # ── No active session — dashboard ────────────────────────────────────────
    if not st.session_state.practice_queue:
        from schedule import get_weighted_topics_with_performance
        algo  = get_weighted_topics_with_performance(progress, all_cards, num_questions=20)
        focus = algo.get("focus_summary","")
        stats = get_today_stats(progress)

        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["streak"]}</div><div class="stat-label">Day streak</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["cards_today"]}</div><div class="stat-label">Today</div></div>', unsafe_allow_html=True)
        xp_t = get_xp_today(progress)
        c3.markdown(f'<div class="stat-tile"><div class="stat-value">{xp_t}</div><div class="stat-label">XP today</div></div>', unsafe_allow_html=True)

        st.markdown(_streak_strip(progress, 7), unsafe_allow_html=True)

        # ── Mode selector ─────────────────────────────────────────────────────
        # Figure out this week's topic names for the card description
        recent_topics = [e for e in algo["topic_plan"] if e.get("weight", 0) >= 4]
        if not recent_topics:
            recent_topics = algo["topic_plan"][-2:]
        recent_names = " · ".join(e["topic"] for e in recent_topics[:3])
        spaced_focus = focus or "Weighted across all topics by recency and your accuracy"

        if not api_key:
            st.warning("Add your Anthropic API key in the sidebar to generate practice questions.")
        else:
            def _start(mode: str):
                spinner_msg = (
                    "Generating questions from this week's classes…"
                    if mode == "week"
                    else "Generating algorithm-weighted questions…"
                )
                with st.spinner(spinner_msg):
                    try:
                        qs = _build_practice_questions(mode=mode)
                        st.session_state.practice_queue    = qs
                        st.session_state.practice_idx      = 0
                        st.session_state.practice_selected = None
                        st.session_state.practice_answered = False
                        st.session_state.practice_correct  = 0
                        st.session_state.practice_mode     = mode
                        st.session_state.session_xp        = 0
                        st.session_state.session_ratings   = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate questions: {e}")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f'<div class="mode-card">'
                    f'<div class="mode-divider"></div>'
                    f'<p class="mode-eyebrow">This week</p>'
                    f'<p class="mode-title">Recent classes</p>'
                    f'<p class="mode-body">{recent_names}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Study this week →", use_container_width=True, type="primary", key="start_week"):
                    _start("week")
            with col2:
                st.markdown(
                    f'<div class="mode-card">'
                    f'<div class="mode-divider"></div>'
                    f'<p class="mode-eyebrow">Spaced repetition</p>'
                    f'<p class="mode-title">Algorithm picks</p>'
                    f'<p class="mode-body">{spaced_focus}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button("Spaced review →", use_container_width=True, key="start_spaced"):
                    _start("spaced")

    # ── Session complete ──────────────────────────────────────────────────────
    elif st.session_state.practice_idx >= len(st.session_state.practice_queue):
        prog    = st.session_state.progress
        new_ach = check_new_achievements(prog, st.session_state.session_ratings)
        if new_ach:
            prog["achievements"] = list(set(prog.get("achievements",[]))|set(new_ach))
            st.session_state.progress = prog
            save_progress(prog)

        sess_xp = st.session_state.session_xp
        qc      = st.session_state.practice_correct
        qt      = len(st.session_state.practice_queue)
        qpct    = int(qc/qt*100) if qt else 0

        st.markdown(
            f'<div class="xp-banner"><div class="xp-number">+{sess_xp}</div>'
            f'<p class="xp-sub">XP earned this session</p></div>',
            unsafe_allow_html=True,
        )

        if get_xp_today(prog) >= DAILY_GOAL_XP:
            st.markdown('<div class="caught-card" style="margin-bottom:12px">'
                        '<p class="caught-eyebrow">Daily goal</p>'
                        '<h2 class="caught-title" style="font-size:1.3rem">Goal reached!</h2>'
                        f'<p class="caught-body">{get_xp_today(prog)} XP today.</p></div>',
                        unsafe_allow_html=True)

        for aid in new_ach:
            a = ACHIEVEMENTS.get(aid,{})
            st.markdown(f'<div class="new-ach-card"><p class="new-ach-label">Achievement unlocked</p>'
                        f'<p class="new-ach-name">{a.get("name","")}</p>'
                        f'<p class="new-ach-desc">{a.get("desc","")}</p></div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="chip-row" style="margin-bottom:20px">'
            f'<span class="chip chip-sage">Streak: {get_today_stats(prog)["streak"]} days</span>'
            f'<span class="chip chip-neutral">{qc}/{qt} correct · {qpct}%</span>'
            f'</div>', unsafe_allow_html=True,
        )

        col = st.columns([1,2,1])[1]
        with col:
            if st.button("Practice again", use_container_width=True, type="primary"):
                st.session_state.practice_queue    = []
                st.session_state.practice_idx      = 0
                st.session_state.session_xp        = 0
                st.session_state.session_ratings   = []
                st.rerun()

    # ── Active question ───────────────────────────────────────────────────────
    else:
        queue = st.session_state.practice_queue
        idx   = st.session_state.practice_idx
        item  = queue[idx]
        pct   = idx / len(queue) * 100

        mode_label = "This week" if st.session_state.get("practice_mode") == "week" else "Spaced review"
        st.markdown(
            f'<div class="progress-row">'
            f'<span class="progress-count">Question {idx+1} of {len(queue)}</span>'
            f'<span class="progress-count" style="color:#B87C65;font-weight:600">{mode_label}</span>'
            f'</div>'
            f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.1f}%"></div></div>',
            unsafe_allow_html=True,
        )

        qh = _html.escape(item.get("question",""))
        th = _html.escape(item.get("topic",""))
        st.markdown(
            f'<div class="flip-card">'
            f'<span class="card-topic-pill">{th}</span>'
            f'<p class="card-q-label">Question</p>'
            f'<p class="card-question">{qh}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

        opts     = item.get("options",[])
        answered = st.session_state.practice_answered
        selected = st.session_state.practice_selected

        if not answered:
            for opt in opts:
                if st.button(opt, key=f"p_opt_{idx}_{opt}", use_container_width=True):
                    st.session_state.practice_selected = opt
                    st.session_state.practice_answered = True
                    st.rerun()
        else:
            correct_letter = item.get("correct","A")
            correct_opt    = next((o for o in opts if o.startswith(correct_letter+".") or o.startswith(correct_letter+" ")), "")
            is_correct     = bool(selected) and (selected.startswith(correct_letter+".") or selected.startswith(correct_letter+" "))
            xp             = XP_CORRECT if is_correct else XP_ATTEMPT

            # Record
            prog = st.session_state.progress
            prog = record_quiz_attempt(prog, item["id"], is_correct)
            prog = add_xp(prog, xp)
            st.session_state.progress = prog

            for opt in opts:
                is_cor = opt == correct_opt
                is_sel = opt == selected
                if is_cor:
                    st.success(f"✓  {opt}")
                elif is_sel:
                    st.error(f"✗  {opt}")
                else:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;{opt}")

            if is_correct:
                _confetti()

            xp_label = f"+{xp} XP — Correct!" if is_correct else f"+{xp} XP — Not quite."
            color    = "#B87C65" if is_correct else "#8C8881"
            st.markdown(f'<p style="color:{color};font-weight:600;margin:8px 0 4px">{xp_label}</p>', unsafe_allow_html=True)
            st.caption(f"Explanation: {item.get('explanation','')}")

            if is_correct:
                st.session_state.practice_correct += 1
            st.session_state.session_xp         += xp
            st.session_state.session_ratings.append(3 if is_correct else 1)

            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Next question", use_container_width=True, type="primary", key=f"p_next_{idx}"):
                    save_progress(st.session_state.progress)
                    st.session_state.practice_idx      += 1
                    st.session_state.practice_selected  = None
                    st.session_state.practice_answered  = False
                    st.rerun()

        if st.button("End session", key="p_end", type="secondary"):
            save_progress(st.session_state.progress)
            st.session_state.practice_queue    = []
            st.session_state.practice_idx      = 0
            st.session_state.practice_selected = None
            st.session_state.practice_answered = False
            st.rerun()

# ════════════════════════════════════════════ REVIEW (FLASHCARDS) ════════════
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
        counts     = count_due(all_cards, progress)
        card_total = counts["due"] + counts["new"]

        if card_total > 0:
            st.markdown(
                f'<div class="hero-card" style="margin-top:12px">'
                f'<p class="hero-eyebrow">Spaced repetition review</p>'
                f'<h2 class="hero-title">{card_total} cards due</h2>'
                f'<p class="hero-body">{counts["due"]} scheduled reviews · {counts["new"]} new cards.<br>'
                f'SM-2 algorithm schedules each card at the optimal moment for long-term retention.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )
            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Start review", use_container_width=True, type="primary"):
                    q = get_due_cards(all_cards, progress)
                    st.session_state.flash_queue     = [dict(c, type="card") for c in q]
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
                '<h2 class="caught-title">No cards due</h2>'
                '<p class="caught-body">SM-2 schedule is clear. Use Practice for more retrieval practice.</p>'
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
            fc      = st.session_state.flash_correct
            ft      = sum(1 for x in queue if x.get("type","card")=="card")
            qc      = st.session_state.session_quiz_correct
            qt      = st.session_state.session_quiz_total
            fpct    = int(fc / ft * 100) if ft else 0
            qpct    = int(qc / qt * 100) if qt else 0
            chips   = f'<span class="chip chip-sage">Streak: {get_today_stats(prog)["streak"]} days</span>'
            if ft: chips += f'<span class="chip chip-neutral">Flashcards: {fc}/{ft} · {fpct}%</span>'
            if qt: chips += f'<span class="chip chip-neutral">Quiz: {qc}/{qt} · {qpct}%</span>'
            st.markdown(f'<div class="chip-row" style="margin-bottom:20px">{chips}</div>', unsafe_allow_html=True)

            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Back to dashboard", use_container_width=True, type="primary"):
                    st.session_state.flash_queue         = []
                    st.session_state.flash_idx           = 0
                    st.session_state.session_xp          = 0
                    st.session_state.session_ratings     = []
                    st.session_state.quiz_selected       = None
                    st.session_state.quiz_answered       = False
                    st.session_state.session_quiz_correct = 0
                    st.session_state.session_quiz_total  = 0
                    st.rerun()

        # Active flashcard
        else:
            card = queue[idx]
            pct  = idx / len(queue) * 100
            fh   = _html.escape(card.get("front",""))
            bh   = _html.escape(card.get("back",""))
            th   = _html.escape(card.get("topic",""))

            st.markdown(
                f'<div class="progress-row">'
                f'<span class="progress-count">Card {idx+1} of {len(queue)}</span>'
                f'<span class="progress-count">{int(pct)}%</span>'
                f'</div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.1f}%"></div></div>',
                unsafe_allow_html=True,
            )

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
                    st.session_state.flash_idx       += 1
                    st.session_state.flash_flipped    = False
                    st.rerun()

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("Again\nForgot it", use_container_width=True, help="Forgot"): _rate(1)
                with c2:
                    if st.button("Hard\nStruggled",  use_container_width=True, help="Struggled"): _rate(2)
                with c3:
                    if st.button("Good\nKnew it",    use_container_width=True, help="Knew it"): _rate(3)
                with c4:
                    if st.button("Easy\nToo easy",   use_container_width=True, help="Too easy"): _rate(4)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("End review", key="end_sess", type="secondary"):
                save_progress(st.session_state.progress)
                st.session_state.flash_queue   = []
                st.session_state.flash_idx     = 0
                st.session_state.flash_flipped = False
                st.rerun()


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
