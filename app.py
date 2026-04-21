"""
app.py — Audit Study Agent · ACCT 40510 · Notre Dame · Spring 2026

Evidence-based study companion: spaced repetition (SM-2), retrieval practice,
confidence-based learning, and immediate feedback.
"""

import html as _html
import json
import os
from datetime import date

import streamlit as st

from agent import generate_summary, generate_study_plan, generate_practice_questions
from flashcards import generate_flashcards, get_due_cards, count_due, load_flashcards, save_flashcards
from progress import load_progress, save_progress, record_review, get_today_stats, get_weak_spots, streak_calendar
from schedule import get_weighted_topics

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Audit Study Agent",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CACHE_FILE = os.path.join(os.path.dirname(__file__), "materials_cache.json")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }

/* Warm linen background */
.stApp { background: #F7F5F1; min-height: 100vh; }
.main .block-container { padding: 2rem 1.75rem 5rem 1.75rem; max-width: 720px; }

/* Header */
.app-header { text-align: center; padding: 12px 0 28px 0; }
.app-title {
    font-family: 'DM Serif Display', serif;
    font-size: 2rem; font-weight: 400; color: #2C2C28;
    letter-spacing: -0.01em; margin: 0 0 6px 0;
}
.app-subtitle {
    font-size: 0.72rem; color: #B0ADA6; font-weight: 500;
    letter-spacing: 0.12em; text-transform: uppercase; margin: 0;
}

/* API banner */
.api-banner {
    background: #FFFFFF; border: 1px solid #EAE7E0;
    border-radius: 18px; padding: 22px 26px; margin-bottom: 24px;
}
.api-banner-text { font-size: 0.88rem; color: #5A5750; line-height: 1.65; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #EDEAE3; border-radius: 14px; padding: 5px; gap: 2px;
    margin-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px; padding: 8px 18px; font-weight: 500; font-size: 0.84rem;
    color: #8A8780; border: none !important; background: transparent;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important; color: #2C2C28 !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
}

/* Flip card */
.flip-card {
    background: #FFFFFF; border-radius: 24px; padding: 60px 52px 52px 52px;
    border: 1px solid #EAE7E0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 16px 48px -8px rgba(0,0,0,0.07);
    text-align: center; min-height: 300px;
    display: flex; flex-direction: column; justify-content: center; align-items: center;
    margin: 16px 0 28px 0; position: relative; overflow: hidden;
}
.flip-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: #C4907A; border-radius: 24px 24px 0 0;
}
.card-topic-pill {
    background: #F5EDE8; color: #C4907A; padding: 5px 14px; border-radius: 100px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
    margin-bottom: 28px; display: inline-block;
}
.card-question { font-size: 1.22rem; color: #2C2C28; line-height: 1.75; font-weight: 500; max-width: 560px; }
.card-q-label { font-size: 0.65rem; color: #C8C4BC; text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600; margin-bottom: 10px; }
.card-divider { width: 36px; height: 1.5px; background: #EAE7E0; margin: 22px auto; border-radius: 2px; }
.card-answer { font-size: 1.02rem; color: #5A5750; line-height: 1.85; max-width: 580px; font-weight: 400; }
.card-question-ghost { font-size: 0.84rem; color: #B0ADA6; max-width: 540px; line-height: 1.6; font-weight: 400; }

/* Progress bar */
.progress-track { background: #EAE7E0; border-radius: 100px; height: 5px; margin-bottom: 6px; }
.progress-fill { background: #C4907A; border-radius: 100px; height: 5px; }
.progress-label { text-align: right; font-size: 0.72rem; color: #B0ADA6; font-weight: 500; margin: 0 0 22px 0; }
.rating-hint { text-align: center; font-size: 0.76rem; color: #B0ADA6; font-weight: 400; margin: 10px 0 14px 0; }

/* Stats */
.stat-tile {
    background: #FFFFFF; border-radius: 18px; padding: 22px 16px 18px 16px; text-align: center;
    border: 1px solid #EAE7E0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.stat-value { font-family: 'DM Serif Display', serif; font-size: 2.2rem; font-weight: 400; color: #2C2C28; line-height: 1; }
.stat-label { font-size: 0.65rem; color: #B0ADA6; margin-top: 8px; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }

/* Streak calendar */
.streak-strip { display: flex; gap: 8px; justify-content: center; margin: 20px 0 4px 0; }
.day-dot { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.66rem; font-weight: 600; }
.day-on  { background: #C4907A; color: #FFFFFF; }
.day-off { background: #EAE7E0; color: #C8C4BC; }
.day-today { box-shadow: 0 0 0 2px #C4907A, 0 0 0 4.5px rgba(196,144,122,0.2); }

/* Weak spots */
.ws-row { margin-bottom: 18px; }
.ws-header { display: flex; justify-content: space-between; font-size: 0.84rem; font-weight: 500; color: #3C3C38; margin-bottom: 6px; }
.ws-pct { color: #8A8780; font-weight: 400; }
.ws-track { background: #EAE7E0; border-radius: 100px; height: 8px; }
.ws-fill  { border-radius: 100px; height: 8px; }

/* Start / complete / caught-up cards */
.start-card, .complete-card {
    background: #FFFFFF; border-radius: 24px; padding: 52px 44px;
    border: 1px solid #EAE7E0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02), 0 16px 48px -8px rgba(0,0,0,0.07);
    text-align: center; margin: 12px 0 24px 0;
}
.caughtup-card {
    background: #F4F8F4; border: 1px solid #C9DEC9;
    border-radius: 24px; padding: 52px 44px; text-align: center; margin: 12px 0 24px 0;
}
.card-emoji  { font-size: 2.8rem; margin-bottom: 18px; line-height: 1; }
.card-title  { font-family: 'DM Serif Display', serif; font-size: 1.45rem; font-weight: 400; color: #2C2C28; margin: 0 0 10px 0; }
.card-body   { font-size: 0.88rem; color: #8A8780; margin: 0 0 34px 0; line-height: 1.65; }
.section-label { font-size: 0.65rem; font-weight: 700; color: #B0ADA6; text-transform: uppercase; letter-spacing: 0.12em; margin: 30px 0 14px 0; }

/* Buttons */
.stButton > button {
    border-radius: 10px !important; font-weight: 500 !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: all 0.15s ease !important;
}
.stButton > button[kind="primary"] {
    background: #C4907A !important; border: none !important; color: white !important;
    box-shadow: 0 2px 10px rgba(196,144,122,0.28) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #B8816A !important;
    box-shadow: 0 4px 16px rgba(196,144,122,0.35) !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "materials":{}, "cache_date":None, "progress":None,
    "flash_queue":[], "flash_idx":0, "flash_flipped":False, "flash_correct":0,
    "last_summary":None, "last_plan":None,
    "last_questions":None, "quiz_answers":{}, "quiz_submitted":False, "quiz_error":None,
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
st.markdown('<div class="app-header"><p class="app-title">📚 Audit Study Agent</p><p class="app-subtitle">ACCT 40510 · Notre Dame · Spring 2026</p></div>', unsafe_allow_html=True)

# ─── API key gate ──────────────────────────────────────────────────────────────
if not api_key:
    st.markdown('<div class="api-banner"><div class="api-banner-text"><strong>🔑 Enter your Anthropic API key to get started</strong><br>Get one at <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a> — $5 of free credit is more than enough.</div></div>', unsafe_allow_html=True)
    entered = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-…")
    if entered:
        st.session_state.api_key = entered
        api_key = entered
        st.rerun()
    st.stop()

# ─── Helpers ───────────────────────────────────────────────────────────────────
def _text(d):
    return "\n\n---\n\n".join(f"[FILE: {n}]\n{m['text']}" for n,m in d.items() if m.get("text","").strip())

def _acc_color(a):
    if a < 0.5: return "#D97B6C"   # warm red-terracotta
    if a < 0.7: return "#D4A853"   # warm amber
    if a < 0.85: return "#7DAA8C"  # sage green
    return "#C4907A"               # terracotta (strong)

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    mats = st.session_state.materials
    st.success(f"✅ {len(mats)} files loaded" if mats else "⚠️ No materials")
    if st.session_state.cache_date: st.caption(f"Updated: {st.session_state.cache_date}")
    st.divider()
    st.caption("Materials auto-refresh from Box after each Tue/Thu class.")
    st.divider()
    if mats:
        if st.button("🔄 Regenerate flashcards"):
            with st.spinner("Generating…"):
                try:
                    w = get_weighted_topics(num_questions=50)
                    notes = {k:v for k,v in mats.items() if v.get("type") in ("notes","reading")}
                    cards = generate_flashcards(api_key, _text(notes), w["topic_plan"])
                    save_flashcards(cards)
                    st.session_state.flash_queue = []
                    st.success(f"✅ {len(cards)} cards ready!")
                    st.rerun()
                except Exception as e: st.error(str(e))
    new_key = st.text_input("Change API key", type="password", placeholder="sk-ant-…")
    if new_key: st.session_state.api_key = new_key; st.rerun()

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_flash, tab_quiz, tab_progress, tab_ai = st.tabs(["🃏  Flashcards","❓  Practice","📊  Progress","🧠  AI Tools"])
mats = st.session_state.materials

# ════════════════════════════════════════ FLASHCARDS ══════════════════════════
with tab_flash:
    progress  = st.session_state.progress
    all_cards = load_flashcards()

    if not all_cards:
        if not mats:
            st.info("No materials yet — your scheduled task will pull them after class.")
        else:
            st.markdown('<div class="start-card"><div class="card-emoji">🃏</div><p class="card-title">Generate your flashcard deck</p><p class="card-body">50 AI-generated cards covering every topic,<br>weighted by what Prof. Morrison actually tests.</p></div>', unsafe_allow_html=True)
            col = st.columns([1,2,1])[1]
            with col:
                if st.button("✨ Generate Flashcards", use_container_width=True, type="primary"):
                    with st.spinner("Creating 50 cards from your course materials…"):
                        try:
                            w = get_weighted_topics(num_questions=50)
                            notes = {k:v for k,v in mats.items() if v.get("type") in ("notes","reading")}
                            cards = generate_flashcards(api_key, _text(notes), w["topic_plan"])
                            save_flashcards(cards); st.session_state.flash_queue = []; st.rerun()
                        except Exception as e: st.error(str(e))

    elif not st.session_state.flash_queue:
        stats  = get_today_stats(progress)
        counts = count_due(all_cards, progress)
        total  = counts["due"] + counts["new"]

        c1,c2,c3 = st.columns(3)
        se = "🔥" if stats["streak"]>=2 else "✨" if stats["streak"]==1 else "💤"
        c1.markdown(f'<div class="stat-tile"><div class="stat-value">{se} {stats["streak"]}</div><div class="stat-label">Streak</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["cards_today"]}</div><div class="stat-label">Today</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="stat-tile"><div class="stat-value">{counts["due"]+counts["new"]}</div><div class="stat-label">Due</div></div>', unsafe_allow_html=True)

        cal = streak_calendar(progress,7); today_str = date.today().isoformat()
        dots = '<div class="streak-strip">'
        for d in cal:
            cls = ("day-on" if d["studied"] else "day-off") + (" day-today" if d["date"]==today_str else "")
            dots += f'<div class="day-dot {cls}">{d["date"][8:]}</div>'
        st.markdown(dots+"</div>", unsafe_allow_html=True)

        if total > 0:
            st.markdown(f'<div class="start-card" style="margin-top:16px"><div class="card-emoji">📖</div><p class="card-title">Ready to study?</p><p class="card-body">{counts["due"]} cards due for review &nbsp;·&nbsp; {counts["new"]} new cards</p></div>', unsafe_allow_html=True)
            col = st.columns([1,2,1])[1]
            with col:
                if st.button("Start session", use_container_width=True, type="primary"):
                    q = get_due_cards(all_cards, progress)
                    st.session_state.flash_queue=q; st.session_state.flash_idx=0
                    st.session_state.flash_flipped=False; st.session_state.flash_correct=0; st.rerun()
        else:
            st.markdown('<div class="caughtup-card"><div class="card-emoji">✅</div><p class="card-title" style="color:#065F46">All caught up!</p><p class="card-body" style="color:#047857;margin:0">No cards due. Come back tomorrow to keep your streak. 🔥</p></div>', unsafe_allow_html=True)

    else:
        queue=st.session_state.flash_queue; idx=st.session_state.flash_idx; flipped=st.session_state.flash_flipped

        if idx >= len(queue):
            correct=st.session_state.flash_correct; total=len(queue)
            pct=int(correct/total*100) if total else 0
            emoji="🎉" if pct>=80 else "💪" if pct>=60 else "📖"
            st.markdown(f'<div class="complete-card"><div class="card-emoji">{emoji}</div><p class="card-title">Session complete!</p><p class="card-body">{correct} / {total} correct &nbsp;·&nbsp; {pct}%<br>{"Cards scheduled — SM-2 will show you exactly when to review next." if pct>=80 else "Missed cards will come back soon. Keep at it!"}</p></div>', unsafe_allow_html=True)
            col=st.columns([1,2,1])[1]
            with col:
                if st.button("Back to dashboard", use_container_width=True, type="primary"):
                    st.session_state.flash_queue=[]; st.session_state.flash_idx=0; st.rerun()
        else:
            card=queue[idx]; pct=idx/len(queue)*100
            st.markdown(f'<div class="progress-track"><div class="progress-fill" style="width:{pct:.1f}%"></div></div><p class="progress-label">{idx} / {len(queue)}</p>', unsafe_allow_html=True)
            fh=_html.escape(card.get("front","")); bh=_html.escape(card.get("back","")); th=_html.escape(card.get("topic",""))

            if not flipped:
                st.markdown(f'<div class="flip-card"><span class="card-topic-pill">{th}</span><div class="card-question">{fh}</div></div>', unsafe_allow_html=True)
                col=st.columns([1,2,1])[1]
                with col:
                    if st.button("Show Answer ↓", use_container_width=True, type="primary"):
                        st.session_state.flash_flipped=True; st.rerun()
            else:
                st.markdown(f'<div class="flip-card"><span class="card-topic-pill">{th}</span><div class="card-q-label">Question</div><div class="card-question-ghost">{fh}</div><div class="card-divider"></div><div class="card-q-label">Answer</div><div class="card-answer">{bh}</div></div>', unsafe_allow_html=True)
                st.markdown('<p class="rating-hint">How well did you know this?</p>', unsafe_allow_html=True)

                def _rate(r):
                    prog=st.session_state.progress; prog=record_review(prog,card["id"],r)
                    st.session_state.progress=prog; save_progress(prog)
                    if r>=3: st.session_state.flash_correct+=1
                    st.session_state.flash_idx+=1; st.session_state.flash_flipped=False; st.rerun()

                c1,c2,c3,c4=st.columns(4)
                with c1:
                    if st.button("🔴  Again", use_container_width=True, help="Forgot — shows again soon"): _rate(1)
                with c2:
                    if st.button("🟡  Hard",  use_container_width=True, help="Got it but struggled"): _rate(2)
                with c3:
                    if st.button("🟢  Good",  use_container_width=True, help="Knew it well"): _rate(3)
                with c4:
                    if st.button("🔵  Easy",  use_container_width=True, help="Way too easy"): _rate(4)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("← End session", key="end_sess"):
                    st.session_state.flash_queue=[]; st.session_state.flash_idx=0; st.session_state.flash_flipped=False; st.rerun()

# ════════════════════════════════════════ PRACTICE QUIZ ═══════════════════════
with tab_quiz:
    if not mats:
        st.info("No materials loaded.")
    else:
        notes_files=[k for k,v in mats.items() if v.get("type") in ("notes","reading")]
        quiz_files =[k for k,v in mats.items() if v.get("type")=="quiz"]

        if not st.session_state.last_questions:
            c1,c2=st.columns(2)
            with c1:
                num_q=st.slider("Questions",3,15,5,key="q_num")
                q_types=st.multiselect("Types",["Multiple Choice","Short Answer","True/False"],default=["Multiple Choice","Short Answer"],key="q_types")
                difficulty=st.select_slider("Difficulty",["Easy","Medium","Hard","Mixed"],value="Mixed",key="q_diff")
            with c2:
                st.markdown("**🗓️ Topics — auto-selected**")
                weighted=get_weighted_topics(num_questions=num_q); topic_plan=weighted["topic_plan"]
                st.info(weighted["summary"])
            if st.button("❓ Generate Questions", type="primary", key="btn_q"):
                with st.spinner("Crafting questions…"):
                    try:
                        w=get_weighted_topics(num_questions=num_q)
                        result=generate_practice_questions(api_key=api_key,notes_text=_text({k:mats[k] for k in notes_files}),quiz_examples=_text({k:mats[k] for k in quiz_files}),num_questions=num_q,question_types=q_types,difficulty=difficulty,topic_plan=w["topic_plan"])
                        st.session_state.last_questions=result; st.session_state.quiz_answers={}; st.session_state.quiz_submitted=False; st.session_state.quiz_error=None
                    except Exception as e: st.session_state.quiz_error=str(e)
            if st.session_state.quiz_error: st.error(st.session_state.quiz_error)

        if st.session_state.last_questions:
            questions=st.session_state.last_questions; submitted=st.session_state.quiz_submitted; answers=st.session_state.quiz_answers
            if st.button("🔄 New Quiz",key="new_quiz"): st.session_state.last_questions=None; st.session_state.quiz_submitted=False; st.rerun()
            st.divider()
            for i,q in enumerate(questions):
                qkey=f"q_{i}"; st.markdown(f"**Q{i+1}. {q.get('question','')}**")
                if submitted:
                    ua=answers.get(qkey,"")
                    if q.get("type") in ("mc","true_false"):
                        ok=ua.strip().upper().startswith(q.get("correct","").strip().upper())
                        (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {ua}")
                        if not ok: st.info(f"Correct: {q['correct']}")
                    else:
                        st.markdown(f"**Your answer:** {ua}" if ua.strip() else "_No answer_"); st.info(f"**Model answer:** {q['correct']}")
                    st.caption(f"💡 {q.get('explanation','')}")
                else:
                    if q.get("type") in ("mc","true_false"):
                        choice=st.radio(f"Q{i+1}",q.get("options",[]),index=None,key=qkey,label_visibility="collapsed"); answers[qkey]=choice or ""
                    else: answers[qkey]=st.text_area(f"Q{i+1}",key=qkey,height=96,placeholder="Type your answer…",label_visibility="collapsed")
                st.divider()
            if not submitted:
                if st.button("✅ Submit & Grade",type="primary",key="submit_q"): st.session_state.quiz_answers=answers; st.session_state.quiz_submitted=True; st.rerun()
            else:
                gradeable=[q for q in questions if q.get("type") in ("mc","true_false")]
                if gradeable:
                    nc=sum(1 for i,q in enumerate(questions) if q.get("type") in ("mc","true_false") and answers.get(f"q_{i}","").strip().upper().startswith(q.get("correct","").strip().upper()))
                    pct=int(nc/len(gradeable)*100); st.metric(f"{'🎉' if pct>=80 else '💪'} Score",f"{nc}/{len(gradeable)}",f"{pct}%")
                md=f"# Quiz Results — {date.today()}\n\n"+"".join(f"**Q{i+1}. {q['question']}**\n- Yours: {answers.get(f'q_{i}','')}\n- Correct: {q['correct']}\n- Why: {q['explanation']}\n\n" for i,q in enumerate(questions))
                st.download_button("⬇️ Download results",md,f"quiz_{date.today()}.md","text/markdown")

# ════════════════════════════════════════ PROGRESS ════════════════════════════
with tab_progress:
    progress=st.session_state.progress; all_cards=load_flashcards(); stats=get_today_stats(progress)
    c1,c2,c3,c4=st.columns(4)
    se="🔥" if stats["streak"]>=2 else "✨" if stats["streak"]==1 else "💤"
    c1.markdown(f'<div class="stat-tile"><div class="stat-value">{se} {stats["streak"]}</div><div class="stat-label">Streak</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["cards_today"]}</div><div class="stat-label">Today</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["longest_streak"]}</div><div class="stat-label">Best</div></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="stat-tile"><div class="stat-value">{stats["total_reviews"]}</div><div class="stat-label">All Time</div></div>', unsafe_allow_html=True)

    st.markdown('<p class="section-label">Last 7 Days</p>', unsafe_allow_html=True)
    cal=streak_calendar(progress,7); today_str=date.today().isoformat()
    dots='<div class="streak-strip">'
    for d in cal:
        cls=("day-on" if d["studied"] else "day-off")+(" day-today" if d["date"]==today_str else "")
        dots+=f'<div class="day-dot {cls}">{d["date"][8:]}</div>'
    st.markdown(dots+"</div>", unsafe_allow_html=True)

    if all_cards:
        weak=get_weak_spots(progress,all_cards)
        if weak:
            st.markdown('<p class="section-label">⚠️ Weakest Topics — focus here</p>', unsafe_allow_html=True)
            for ws in weak[:8]:
                pct=int(ws["accuracy"]*100); color=_acc_color(ws["accuracy"])
                st.markdown(f'<div class="ws-row"><div class="ws-header"><span>{ws["topic"]}</span><span class="ws-pct">{ws["correct"]}/{ws["total"]} · {pct}%</span></div><div class="ws-track"><div class="ws-fill" style="width:{pct}%;background:{color}"></div></div></div>', unsafe_allow_html=True)
        else: st.info("Study at least 3 cards per topic to see accuracy data.")
    else: st.info("Generate flashcards on the 🃏 tab to start tracking progress.")

    with st.expander("⚠️ Reset all progress"):
        st.warning("Clears all streaks and review history. Cannot be undone.")
        if st.button("Reset progress",type="secondary"):
            from progress import _DEFAULTS
            st.session_state.progress=_DEFAULTS.copy(); save_progress(st.session_state.progress); st.rerun()

# ════════════════════════════════════════ AI TOOLS ════════════════════════════
with tab_ai:
    if not mats: st.info("No materials loaded.")
    else:
        tool=st.radio("",["📄 Summary","📅 Study Plan"],horizontal=True,label_visibility="collapsed")
        if "Summary" in tool:
            st.markdown('<p class="section-label">Exam-ready summary of your materials</p>', unsafe_allow_html=True)
            sel=st.multiselect("Files",list(mats.keys()),default=list(mats.keys()))
            if st.button("✨ Generate Summary",type="primary"):
                with st.spinner("Summarizing…"):
                    st.session_state.last_summary=generate_summary(api_key,_text({k:mats[k] for k in sel}))
            if st.session_state.last_summary:
                st.markdown(st.session_state.last_summary)
                st.download_button("⬇️ Download",st.session_state.last_summary,f"summary_{date.today()}.md","text/markdown")
        else:
            st.markdown('<p class="section-label">Personalized schedule · spaced repetition · active recall</p>', unsafe_allow_html=True)
            c1,c2=st.columns(2)
            with c1:
                nc=st.date_input("Next class",value=date.today()); exam=st.date_input("Exam date"); hrs=st.slider("Hours/day",0.5,4.0,1.5,0.5)
            with c2: focus=st.text_area("Topics to prioritize (optional)",height=120,placeholder="e.g. sampling, ethics")
            if st.button("📅 Generate Plan",type="primary"):
                with st.spinner("Building your plan…"):
                    st.session_state.last_plan=generate_study_plan(api_key,_text(mats),str(nc),str(exam),hrs,focus)
            if st.session_state.last_plan:
                st.markdown(st.session_state.last_plan)
                st.download_button("⬇️ Download",st.session_state.last_plan,f"plan_{date.today()}.md","text/markdown")
