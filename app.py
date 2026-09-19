import streamlit as st
import json
import os
import datetime
import time
import uuid
import re
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# -------------------------------------------------------------------
# APP CONFIGURATION & EXPANDED STYLING
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Auto-Scheduler Enterprise", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dynamic CSS Theme Engine
def apply_custom_theme(theme_mode, accent_color):
    bg_color = "#0e1117" if theme_mode == "Dark / OLED" else "#ffffff"
    text_color = "#ffffff" if theme_mode == "Dark / OLED" else "#111111"
    card_bg = "rgba(255, 255, 255, 0.05)" if theme_mode == "Dark / OLED" else "rgba(0, 0, 0, 0.03)"
    
    st.markdown(f"""
        <style>
        .main {{ background-color: {bg_color}; color: {text_color}; }}
        .stMetric {{ background-color: {card_bg}; padding: 12px; border-radius: 10px; border: 1px solid {accent_color}33; }}
        .stButton>button {{ border-radius: 8px; border: 1px solid {accent_color}; }}
        </style>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------------
# COMPREHENSIVE COURSE DATABASE GENERATOR (1,000 COURSES)
# -------------------------------------------------------------------
@st.cache_data
def load_expanded_course_database():
    """Generates and caches an expansive database of 1,000 academic courses across all fields."""
    categories = {
        "Computer Science & AI": ["Data Structures", "Algorithms", "Machine Learning", "Operating Systems", "Cybersecurity", "Web Development", "Computer Vision", "NLP", "Cloud Computing", "Database Systems"],
        "Mathematics & Statistics": ["Calculus AB", "Calculus BC", "Multivariable Calculus", "Linear Algebra", "Differential Equations", "Probability Theory", "Mathematical Statistics", "Abstract Algebra", "Discrete Math", "Real Analysis"],
        "Physics & Engineering": ["Physics 1", "Physics C Mechanics", "Thermodynamics", "Quantum Mechanics", "Organic Chemistry", "General Chemistry", "Statics", "Circuit Analysis", "Fluid Mechanics", "Materials Science"],
        "Biology & Medicine": ["General Biology", "Cell Biology", "Genetics", "Human Anatomy", "Physiology", "Microbiology", "Immunology", "Neuroscience", "Biochemistry", "Pharmacology"],
        "Economics & Business": ["Microeconomics", "Macroeconomics", "Financial Accounting", "Corporate Finance", "Econometrics", "Marketing Management", "Business Strategy", "Operations Management", "Investments", "Organizational Behavior"],
        "Humanities & Social Sciences": ["US History", "World History", "Psychology", "Sociology", "Political Science", "Philosophy Ethics", "Macro Sociology", "Cognitive Psychology", "Micro Anthropology", "International Relations"],
        "Languages & Arts": ["Spanish I", "AP Spanish", "French I", "AP French", "German I", "Studio Art", "Music Theory", "Digital Photography", "Graphic Design", "Creative Writing"]
    }
    
    levels = ["Middle School", "High School", "AP", "College"]
    database = {}
    
    count = 1
    for cat, topics in categories.items():
        for topic in topics:
            for lvl in levels:
                for var in ["I", "II", "Advanced", "Honors"]:
                    course_id = f"CRS-{count:04d}"
                    course_name = f"{lvl} {topic} {var}"
                    diff = 5 if lvl == "College" or "AP" in lvl else (4 if "Advanced" in var or "Honors" in var else 3)
                    hours = diff * 1.5 + 1.0
                    
                    database[course_name] = {
                        "id": course_id,
                        "category": cat,
                        "level": lvl,
                        "difficulty": int(diff),
                        "hours": float(hours),
                        "reasoning": f"Standardized {lvl} level curriculum covering foundational and advanced concepts in {topic} ({var})."
                    }
                    count += 1
                    if count > 1000:
                        break
                if count > 1000:
                    break
            if count > 1000:
                break
        if count > 1000:
            break
            
    return database

EXPANDED_COURSES = load_expanded_course_database()

# -------------------------------------------------------------------
# DATA PERSISTENCE ENGINE
# -------------------------------------------------------------------
DATA_FILE = "user_data.json"

def load_user_data():
    default_structure = {
        "user_schedule": [],
        "projects": [],
        "distractions": [],
        "deliverables": {},
        "streaks": {"last_active": str(datetime.date.today()), "count": 1},
        "xp": 0,
        "settings": {"theme": "Dark / OLED", "accent": "#00FFAA", "pomo_work": 25, "pomo_break": 5}
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                for key, val in default_structure.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception:
            return default_structure
    return default_structure

def save_user_data():
    data = {
        "user_schedule": st.session_state.get("user_schedule", []),
        "projects": st.session_state.get("projects", []),
        "distractions": st.session_state.get("distractions", []),
        "deliverables": st.session_state.get("deliverables", {}),
        "streaks": st.session_state.get("streaks", {"last_active": str(datetime.date.today()), "count": 1}),
        "xp": st.session_state.get("xp", 0),
        "settings": st.session_state.get("settings", {})
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        st.error(f"Error saving data: {e}")

# Initialize Session State
saved_data = load_user_data()
for key in ["user_schedule", "projects", "distractions", "deliverables", "streaks", "xp", "settings"]:
    if key not in st.session_state:
        st.session_state[key] = saved_data[key]

# Apply Theme Settings
apply_custom_theme(st.session_state.settings.get("theme", "Dark / OLED"), st.session_state.settings.get("accent", "#00FFAA"))

# Helper Function
def format_hours_and_mins(total_minutes):
    total_minutes = max(0, int(round(total_minutes)))
    hrs = total_minutes // 60
    mins = total_minutes % 60
    if hrs == 0:
        return f"{mins} mins"
    elif mins == 0:
        return f"{hrs} hrs"
    return f"{hrs} hrs {mins} mins"

# -------------------------------------------------------------------
# SIDEBAR CONTROLS & CUSTOMIZATION
# -------------------------------------------------------------------
st.sidebar.title("⚡ System Control")
st.sidebar.markdown(f"🔥 **Streak:** `{st.session_state.streaks['count']} Days` | ⭐ **XP:** `{st.session_state.xp}`")

# Theme & Customization Preferences
with st.sidebar.expander("🎨 Appearance & Themes"):
    theme_choice = st.selectbox("Visual Theme", ["Dark / OLED", "Light Mode"], index=0 if st.session_state.settings.get("theme") == "Dark / OLED" else 1)
    accent_choice = st.color_picker("Accent Color", value=st.session_state.settings.get("accent", "#00FFAA"))
    if theme_choice != st.session_state.settings.get("theme") or accent_choice != st.session_state.settings.get("accent"):
        st.session_state.settings["theme"] = theme_choice
        st.session_state.settings["accent"] = accent_choice
        save_user_data()
        st.rerun()

# Timer Controls Settings
with st.sidebar.expander("⏱️ Pomodoro Settings"):
    p_work = st.number_input("Work Sprint (mins)", min_value=5, max_value=120, value=st.session_state.settings.get("pomo_work", 25))
    p_break = st.number_input("Break Length (mins)", min_value=1, max_value=30, value=st.session_state.settings.get("pomo_break", 5))
    if p_work != st.session_state.settings.get("pomo_work") or p_break != st.session_state.settings.get("pomo_break"):
        st.session_state.settings["pomo_work"] = p_work
        st.session_state.settings["pomo_break"] = p_break
        save_user_data()

# API Key Handling
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Required for custom AI syllabus analysis.")
if api_key:
    genai.configure(api_key=api_key)

st.sidebar.divider()
if st.sidebar.button("🗑️ Reset All User Data"):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    st.rerun()

# -------------------------------------------------------------------
# MAIN NAVIGATION & TABS
# -------------------------------------------------------------------
st.title("⚡ Smart Auto-Scheduler Enterprise")
st.caption(f"Accessing database of **{len(EXPANDED_COURSES):,}** courses across STEM, Humanities, Business & Health.")

tabs = st.tabs([
    "📚 Course Selection (1,000 Database)", 
    "📅 Daily Allocator & Deliverables", 
    "🚀 Project Engine", 
    "⏱️ Active Focus Sprint", 
    "📊 Timeline & Guardrails"
])

# -------------------------------------------------------------------
# TAB 1: EXPANDED COURSE SELECTION
# -------------------------------------------------------------------
with tabs[0]:
    st.header("Academic Roster Configuration")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        cat_filter = st.multiselect("Filter Discipline:", options=list(set(c["category"] for c in EXPANDED_COURSES.values())), default=[])
    with col_f2:
        lvl_filter = st.multiselect("Filter Academic Level:", options=["Middle School", "High School", "AP", "College"], default=[])

    # Filter Course Options
    available_courses = EXPANDED_COURSES
    if cat_filter:
        available_courses = {k: v for k, v in available_courses.items() if v["category"] in cat_filter}
    if lvl_filter:
        available_courses = {k: v for k, v in available_courses.items() if v["level"] in lvl_filter}

    # Selected Courses Search Bar
    existing_selected = [c["course"] for c in st.session_state.user_schedule if c["course"] in available_courses]
    selected_course_names = st.multiselect(
        f"Search & Select Courses ({len(available_courses)} Available):",
        options=sorted(list(available_courses.keys())),
        default=existing_selected
    )

    # Sync Selection Changes
    updated_schedule = []
    for c_name in selected_course_names:
        c_data = EXPANDED_COURSES[c_name]
        updated_schedule.append({
            "course": c_name,
            "level": c_data["level"],
            "difficulty": c_data["difficulty"],
            "hours": c_data["hours"],
            "reasoning": c_data["reasoning"]
        })

    # Preserve Custom AI Classes
    for c in st.session_state.user_schedule:
        if c.get("level") == "Custom":
            updated_schedule.append(c)

    if updated_schedule != st.session_state.user_schedule:
        st.session_state.user_schedule = updated_schedule
        save_user_data()

    # Custom Course Addition via AI
    with st.expander("➕ Add Custom Class via Gemini AI Syllabus Parser"):
        custom_name = st.text_input("Course Title", max_chars=60)
        custom_syllabus = st.text_area("Paste Syllabus Text", max_chars=2000)
        if st.button("Analyze & Add Custom Course"):
            if not api_key:
                st.error("API Key required in sidebar.")
            elif custom_name and custom_syllabus:
                with st.spinner("AI analyzing course difficulty..."):
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"Analyze syllabus for '{custom_name}': {custom_syllabus}\nRespond strictly in raw JSON: {{\"difficulty\": <1-5>, \"recommended_weekly_hours\": <float>, \"reasoning\": \"<text>\"}}"
                        res = model.generate_content(prompt)
                        clean_text = res.text.replace("```json", "").replace("```", "").strip()
                        ai_data = json.loads(clean_text)
                        
                        st.session_state.user_schedule.append({
                            "course": custom_name,
                            "level": "Custom",
                            "difficulty": max(1, min(5, int(ai_data.get("difficulty", 3)))),
                            "hours": float(ai_data.get("recommended_weekly_hours", 4.0)),
                            "reasoning": str(ai_data.get("reasoning", "Custom syllabus parsed by AI."))
                        })
                        save_user_data()
                        st.success(f"Added {custom_name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error parsing syllabus: {e}")

    # Active Course Roster Display
    if st.session_state.user_schedule:
        st.subheader("Your Active Course Roster")
        for c in st.session_state.user_schedule:
            st.info(f"**[{c['level']}] {c['course']}** — Difficulty: `{c['difficulty']}/5` | Share: `~{c['hours']} hrs/week`\n\n_{c['reasoning']}_")

# -------------------------------------------------------------------
# TAB 2: DAILY TIME ALLOCATOR
# -------------------------------------------------------------------
with tabs[1]:
    st.header("Daily Allocator & Specific Task Deliverables")
    
    if not st.session_state.user_schedule:
        st.warning("⚠️ Please select courses in Tab 1 to generate allocations.")
    else:
        st.subheader("Target Available Self-Study Window")
        c1, c2 = st.columns(2)
        with c1:
            alloc_h = st.number_input("Hours", min_value=0, max_value=16, value=4, step=1)
        with c2:
            alloc_m = st.number_input("Minutes", min_value=0, max_value=55, value=0, step=5)
            
        total_minutes = (alloc_h * 60) + alloc_m
        total_difficulty = sum(c["difficulty"] for c in st.session_state.user_schedule) or 1

        st.divider()
        st.subheader(f"Weighted Breakdown ({format_hours_and_mins(total_minutes)} Total)")
        
        for c in st.session_state.user_schedule:
            allocated_mins = (c["difficulty"] / total_difficulty) * total_minutes
            st.markdown(f"#### • **[{c['level']}] {c['course']}** → `{format_hours_and_mins(allocated_mins)}`")
            
            # Task Deliverables binding
            deliv_key = f"deliv_{c['course']}"
            current_val = st.session_state.deliverables.get(c['course'], "")
            new_val = st.text_input(f"Today's specific goal for {c['course']}:", value=current_val, key=deliv_key)
            if new_val != current_val:
                st.session_state.deliverables[c['course']] = new_val
                save_user_data()

# -------------------------------------------------------------------
# TAB 3: PROJECT ENGINE
# -------------------------------------------------------------------
with tabs[2]:
    st.header("🚀 Project & Assignment Engine")
    
    with st.form("project_form", clear_on_submit=True):
        p_title = st.text_input("Project Title")
        p_hrs = st.number_input("Total Estimated Hours Required", min_value=0.5, max_value=100.0, value=6.0, step=0.5)
        p_due = st.date_input("Due Date", min_value=datetime.date.today())
        
        if st.form_submit_button("Add Project"):
            if p_title:
                st.session_state.projects.append({
                    "id": str(uuid.uuid4()),
                    "title": p_title,
                    "total_hours": float(p_hrs),
                    "deadline": str(p_due)
                })
                save_user_data()
                st.success(f"Project '{p_title}' added!")
                st.rerun()

    if st.session_state.projects:
        st.subheader("Active Projects Workload Breakdown")
        active_projects = []
        for p in st.session_state.projects:
            due_date = datetime.datetime.strptime(p["deadline"], "%Y-%m-%d").date()
            days_left = max(1, (due_date - datetime.date.today()).days)
            daily_req_mins = (p["total_hours"] * 60) / days_left
            
            col_info, col_del = st.columns([3, 1])
            with col_info:
                st.write(f"**{p['title']}** | Due: `{p['deadline']}` ({days_left} days left)")
                st.markdown(f"👉 **Required Daily Work:** `{format_hours_and_mins(daily_req_mins)}` / day")
            with col_del:
                if st.button("Complete / Clear", key=f"p_del_{p['id']}"):
                    st.session_state.xp += 50
                    st.toast("Project Completed! +50 XP", icon="⭐")
                    continue
            active_projects.append(p)
            st.divider()

        if len(active_projects) != len(st.session_state.projects):
            st.session_state.projects = active_projects
            save_user_data()
            st.rerun()

# -------------------------------------------------------------------
# TAB 4: FOCUS TIMER & DISTRACTION LOG
# -------------------------------------------------------------------
with tabs[3]:
    st.header("⏱️ Active Focus Session")
    
    c_timer, c_trap = st.columns([2, 1])
    with c_timer:
        st.subheader("Pomodoro Sprint")
        courses_available = [c["course"] for c in st.session_state.user_schedule] if st.session_state.user_schedule else ["General Focus"]
        target_course = st.selectbox("Target Course", courses_available)
        sprint_mins = st.number_input("Sprint Length (Minutes)", min_value=1, max_value=120, value=st.session_state.settings.get("pomo_work", 25))
        
        if st.button("▶️ Start Focus Sprint"):
            ph = st.empty()
            end_time = time.time() + (sprint_mins * 60)
            while time.time() < end_time:
                remaining = int(end_time - time.time())
                mins, secs = divmod(remaining, 60)
                ph.markdown(f"# ⏳ `{mins:02d}:{secs:02d}`")
                ph.caption(f"Focusing on: **{target_course}**")
                time.sleep(1)
            ph.success("🎉 Sprint Complete! Take a break.")
            st.session_state.xp += 15
            save_user_data()
            st.toast("Earned +15 XP!", icon="⭐")

    with c_trap:
        st.subheader("🧠 Distraction Trap")
        d_thought = st.text_input("Log Distraction", key="dist_thought_input")
        if st.button("Trap Thought"):
            if d_thought:
                st.session_state.distractions.append({
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "thought": d_thought
                })
                save_user_data()
                st.toast("Thought trapped!", icon="🧠")
                st.rerun()

        if st.session_state.distractions:
            st.divider()
            for d in reversed(st.session_state.distractions[-5:]):
                st.caption(f"• **[{d['time']}]** {d['thought']}")

# -------------------------------------------------------------------
# TAB 5: TIMELINE & HEALTH GUARDRAILS
# -------------------------------------------------------------------
with tabs[4]:
    st.header("📊 Daily Schedule Visualizer & Guardrails")

    c_s, c_sch = st.columns(2)
    with c_s:
        sleep_hours = st.number_input("Sleep Target (Hours)", min_value=4.0, max_value=12.0, value=8.0, step=0.5)
    with c_sch:
        school_hours = st.number_input("In-Class / School Target (Hours)", min_value=0.0, max_value=12.0, value=6.0, step=0.5)

    study_hours = total_minutes / 60.0 if 'total_minutes' in locals() else 4.0
    free_hours = max(0.0, 24.0 - sleep_hours - school_hours - study_hours)

    timeline_df = pd.DataFrame([
        {"Category": "Sleep", "Hours": sleep_hours},
        {"Category": "School / Class", "Hours": school_hours},
        {"Category": "Self-Study", "Hours": study_hours},
        {"Category": "Free Time", "Hours": free_hours}
    ])
    timeline_df = timeline_df[timeline_df["Hours"] > 0]

    fig = px.bar(
        timeline_df, 
        x="Hours", 
        y="Category", 
        orientation='h', 
        color="Category",
        text="Hours",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig.update_layout(height=280, showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True)

    if sleep_hours + school_hours + study_hours > 24.0:
        st.error("🚨 Overcommitment Warning: Total commitments exceed 24 hours!")
    else:
        st.success(f"✅ Schedule Balanced: `{format_hours_and_mins(free_hours * 60)}` remaining for relaxation today.")
