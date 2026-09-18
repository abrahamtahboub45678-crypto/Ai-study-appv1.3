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
# APP CONFIGURATION & BRANDING
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Auto-Scheduler Engine", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { padding-top: 1rem; }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# HELPER UTILITIES
# -------------------------------------------------------------------
def format_hours_and_mins(total_minutes):
    """Converts total minutes into a formatted human-readable string."""
    total_minutes = max(0, int(round(total_minutes)))
    hrs = total_minutes // 60
    mins = total_minutes % 60
    if hrs == 0:
        return f"{mins} mins"
    elif mins == 0:
        return f"{hrs} hrs"
    return f"{hrs} hrs {mins} mins"

def sanitize_string(text):
    """Sanitizes user text inputs for rendering safe Markdown."""
    return re.sub(r'[^\w\s\-\.\,\(\)\:\/\!\?]', '', str(text))

# -------------------------------------------------------------------
# LOCAL PERSISTENCE ENGINE (STRUCTURAL FIXES)
# -------------------------------------------------------------------
DATA_FILE = "user_data.json"

def load_user_data():
    """Loads user configuration safely with fallback defaults."""
    default_structure = {
        "user_schedule": [],
        "projects": [],
        "distractions": [],
        "deliverables": {},
        "streaks": {"last_active": str(datetime.date.today()), "count": 1},
        "xp": 0
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                # Ensure all default keys exist
                for key, val in default_structure.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception:
            st.warning("⚠️ Local data file corrupted. Re-initializing safe default profile.")
            return default_structure
    return default_structure

def save_user_data():
    """Persists current session state to disk safely."""
    data = {
        "user_schedule": st.session_state.get("user_schedule", []),
        "projects": st.session_state.get("projects", []),
        "distractions": st.session_state.get("distractions", []),
        "deliverables": st.session_state.get("deliverables", {}),
        "streaks": st.session_state.get("streaks", {"last_active": str(datetime.date.today()), "count": 1}),
        "xp": st.session_state.get("xp", 0)
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        st.error(f"Failed to save state to local storage: {e}")

# Initialize Session States
saved_data = load_user_data()
for key in ["user_schedule", "projects", "distractions", "deliverables", "streaks", "xp"]:
    if key not in st.session_state:
        st.session_state[key] = saved_data[key]

# Update Gamified Streaks
today_str = str(datetime.date.today())
last_active = st.session_state.streaks.get("last_active", today_str)
if last_active != today_str:
    last_date = datetime.datetime.strptime(last_active, "%Y-%m-%d").date()
    if (datetime.date.today() - last_date).days == 1:
        st.session_state.streaks["count"] += 1
    elif (datetime.date.today() - last_date).days > 1:
        st.session_state.streaks["count"] = 1
    st.session_state.streaks["last_active"] = today_str
    save_user_data()

# -------------------------------------------------------------------
# COURSE DATABASE LOADER
# -------------------------------------------------------------------
@st.cache_data
def load_preset_courses():
    """Loads courses.json safely with robust fallback defaults."""
    if os.path.exists("courses.json"):
        try:
            with open("courses.json", "r") as f:
                return json.load(f)
        except Exception:
            pass
    # Default fallback library if file missing
    return {
        "AP Calculus BC": {"level": "AP", "difficulty": 5, "hours": 8, "reasoning": "Advanced calculus, series, and vectors."},
        "AP Physics 1": {"level": "AP", "difficulty": 5, "hours": 7, "reasoning": "Algebra-based mechanics and dynamics."},
        "High School Chemistry": {"level": "High School", "difficulty": 3, "hours": 4, "reasoning": "Stoichiometry and atomic bonding."},
        "College Computer Science A": {"level": "College", "difficulty": 4, "hours": 6, "reasoning": "Data structures and OOP concepts."}
    }

PRESET_COURSES = load_preset_courses()

# -------------------------------------------------------------------
# SIDEBAR CONTROLS & GAMIFICATION METRICS
# -------------------------------------------------------------------
st.sidebar.title("⚡ Control Center")
st.sidebar.markdown(f"🔥 **Daily Streak:** `{st.session_state.streaks['count']} Days` | ⭐ **XP:** `{st.session_state.xp}`")

# API Key Handling
api_key = st.sidebar.text_input("Gemini API Key (Optional)", type="password", help="Required for custom AI syllabus parsing.")
if api_key:
    genai.configure(api_key=api_key)

st.sidebar.divider()

# Reset Option
if st.sidebar.button("🗑️ Reset All Data", help="Clears local storage and starts fresh."):
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    st.session_state.clear()
    st.rerun()

# -------------------------------------------------------------------
# MAIN APP NAVIGATION
# -------------------------------------------------------------------
st.title("⚡ Smart Auto-Scheduler")
st.caption("AI-Powered Time Allocation, Project Execution Engine, Focus Timers, and Health Protection.")

tabs = st.tabs([
    "📚 Class Load & Setup", 
    "📅 Today's Study Allocation", 
    "🚀 Project Engine", 
    "⏱️ Active Focus Sprint", 
    "📊 Timeline & Health Guardrails"
])

# -------------------------------------------------------------------
# TAB 1: COURSE LOAD SETUP
# -------------------------------------------------------------------
with tabs[0]:
    st.header("Academic Course Configuration")
    
    level_filter = st.multiselect(
        "Filter Preset Library by Level:",
        options=["Middle School", "High School", "AP", "College"],
        default=["Middle School", "High School", "AP", "College"]
    )
    if not level_filter:
        level_filter = ["Middle School", "High School", "AP", "College"]

    filtered_presets = {
        name: data for name, data in PRESET_COURSES.items() 
        if data.get("level") in level_filter
    }

    # Selected Courses
    existing_preset_names = [c["course"] for c in st.session_state.user_schedule if c.get("course") in filtered_presets]
    selected_presets = st.multiselect(
        "Select Active Courses:",
        options=list(filtered_presets.keys()),
        default=existing_preset_names
    )

    # Sync Selection Changes
    new_schedule = []
    for course_name in selected_presets:
        data = PRESET_COURSES[course_name]
        new_schedule.append({
            "course": course_name,
            "level": data["level"],
            "difficulty": max(1, min(5, data["difficulty"])),
            "hours": data["hours"],
            "reasoning": data["reasoning"]
        })
    
    # Preserve Custom Courses
    for c in st.session_state.user_schedule:
        if c.get("level") == "Custom":
            new_schedule.append(c)

    if new_schedule != st.session_state.user_schedule:
        st.session_state.user_schedule = new_schedule
        save_user_data()

    # Add Custom Course via AI
    with st.expander("➕ Add Custom Class / AI Syllabus Analysis"):
        custom_name = st.text_input("Custom Course Name", max_chars=50)
        custom_syllabus = st.text_area("Paste Syllabus or Description", max_chars=2000)
        
        if st.button("🤖 Analyze & Add Course"):
            if not api_key:
                st.error("Gemini API key required in the sidebar for custom analysis!")
            elif custom_name and custom_syllabus:
                with st.spinner("AI analyzing course difficulty..."):
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"""
                        Analyze syllabus for '{custom_name}': {custom_syllabus}
                        Respond ONLY in raw JSON format with no markdown wrappers:
                        {{
                            "difficulty": <number 1 to 5>,
                            "recommended_weekly_hours": <number>,
                            "reasoning": "<short 1 sentence explanation>"
                        }}
                        """
                        res = model.generate_content(prompt)
                        clean_text = res.text.replace("```json", "").replace("```", "").strip()
                        ai_data = json.loads(clean_text)
                        
                        st.session_state.user_schedule.append({
                            "course": sanitize_string(custom_name),
                            "level": "Custom",
                            "difficulty": max(1, min(5, int(ai_data.get("difficulty", 3)))),
                            "hours": int(ai_data.get("recommended_weekly_hours", 4)),
                            "reasoning": sanitize_string(ai_data.get("reasoning", "Custom course."))
                        })
                        save_user_data()
                        st.toast(f"Added {custom_name}!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error analyzing syllabus: {e}")

    # Active Course Roster Display
    if st.session_state.user_schedule:
        st.subheader("Current Active Roster")
        for c in st.session_state.user_schedule:
            diff_badge = "🔥" if c["difficulty"] == 5 else "⭐"
            with st.expander(f"{diff_badge} [{c['level']}] {c['course']} — Difficulty: {c['difficulty']}/5"):
                st.write(f"**Baseline Study Share:** ~{c['hours']} hrs/week")
                st.write(f"**AI/Preset Reasoning:** {c['reasoning']}")

# -------------------------------------------------------------------
# TAB 2: DAILY TIME ALLOCATOR & DELIVERABLES
# -------------------------------------------------------------------
with tabs[1]:
    st.header("Daily Time Allocator & Deliverables")
    
    if not st.session_state.user_schedule:
        st.warning("⚠️ No courses active. Please select courses in Tab 1 first.")
    else:
        st.subheader("Target Available Self-Study Time Today")
        col1, col2 = st.columns(2)
        with col1:
            study_hours = st.number_input("Hours", min_value=0, max_value=16, value=3, step=1, key="alloc_h")
        with col2:
            study_mins = st.number_input("Minutes", min_value=0, max_value=55, value=30, step=5, key="alloc_m")
            
        total_study_minutes_today = (study_hours * 60) + study_mins
        total_difficulty = sum(c["difficulty"] for c in st.session_state.user_schedule) or 1

        st.divider()
        st.subheader(f"Weighted Schedule Allocation ({format_hours_and_mins(total_study_minutes_today)} Total)")
        
        # Calculate Weighted Time Allocation
        for c in st.session_state.user_schedule:
            allocated_minutes = (c["difficulty"] / total_difficulty) * total_study_minutes_today
            formatted_time = format_hours_and_mins(allocated_minutes)
            
            st.markdown(f"#### • **[{c['level']}] {c['course']}** (Diff: {c['difficulty']}/5) → `{formatted_time}`")
            
            # Deliverable Binding
            deliv_key = f"deliv_{c['course']}"
            current_deliv = st.session_state.deliverables.get(c['course'], "")
            new_deliv = st.text_input(
                f"Today's specific deliverable for {c['course']}:", 
                value=current_deliv, 
                placeholder="e.g., Read Chapter 4 and solve problems 1-10",
                key=deliv_key
            )
            if new_deliv != current_deliv:
                st.session_state.deliverables[c['course']] = sanitize_string(new_deliv)
                save_user_data()

# -------------------------------------------------------------------
# TAB 3: PROJECT ENGINE
# -------------------------------------------------------------------
with tabs[2]:
    st.header("🚀 Project Execution Engine")
    st.write("Track deadlines and let the app break down required daily focus time.")

    with st.form("add_project_form", clear_on_submit=True):
        p_name = st.text_input("Project / Assignment Title", max_chars=60)
        p_hours = st.number_input("Estimated Total Hours Needed", min_value=0.5, max_value=100.0, value=5.0, step=0.5)
        p_deadline = st.date_input("Due Date", min_value=datetime.date.today())
        
        if st.form_submit_button("Add Project"):
            if p_name:
                st.session_state.projects.append({
                    "id": str(uuid.uuid4()),
                    "title": sanitize_string(p_name),
                    "total_hours": float(p_hours),
                    "deadline": str(p_deadline)
                })
                save_user_data()
                st.toast(f"Project '{p_name}' added!", icon="🚀")
                st.rerun()

    if st.session_state.projects:
        st.subheader("Active Projects Breakdown")
        remaining_projects = []
        
        for p in st.session_state.projects:
            due_date = datetime.datetime.strptime(p["deadline"], "%Y-%m-%d").date()
            days_remaining = (due_date - datetime.date.today()).days
            
            col_info, col_action = st.columns([3, 1])
            with col_info:
                if days_remaining < 0:
                    st.error(f"⚠️ **{p['title']}** (OVERDUE by {abs(days_remaining)} days!)")
                elif days_remaining == 0:
                    st.warning(f"🚨 **{p['title']}** (DUE TODAY! — Total Work: {p['total_hours']} hrs)")
                else:
                    days_rem_clamped = max(1, days_remaining)
                    daily_needed_mins = (p["total_hours"] * 60) / days_rem_clamped
                    st.write(f"**{p['title']}** | Due in `{days_remaining} days` ({p['deadline']})")
                    st.markdown(f"👉 **Required Daily Work:** `{format_hours_and_mins(daily_needed_mins)}` / day")
            
            with col_action:
                if st.button("Complete / Clear", key=f"del_{p['id']}"):
                    st.session_state.xp += 50
                    st.toast("Project Completed! +50 XP", icon="⭐")
                    continue
            
            remaining_projects.append(p)
            st.divider()

        if len(remaining_projects) != len(st.session_state.projects):
            st.session_state.projects = remaining_projects
            save_user_data()
            st.rerun()

# -------------------------------------------------------------------
# TAB 4: FOCUS TIMER & DISTRACTION TRAP
# -------------------------------------------------------------------
with tabs[3]:
    st.header("⏱️ Active Focus Session")
    
    col_timer, col_trap = st.columns([2, 1])
    
    with col_timer:
        st.subheader("Pomodoro Sprint Engine")
        course_list = [c["course"] for c in st.session_state.user_schedule] if st.session_state.user_schedule else ["General Focus"]
        timer_course = st.selectbox("Select Target Focus Subject", course_list)
        timer_minutes = st.number_input("Sprint Duration (Mins)", min_value=1, max_value=120, value=25, step=5)
        
        if st.button("▶️ Launch Focus Sprint"):
            timer_ph = st.empty()
            total_secs = int(timer_minutes * 60)
            
            # Non-blocking timestamp based timer loop
            end_time = time.time() + total_secs
            while time.time() < end_time:
                rem_secs = int(end_time - time.time())
                mins, secs = divmod(rem_secs, 60)
                timer_ph.markdown(f"# ⏳ `{mins:02d}:{secs:02d}`")
                timer_ph.caption(f"Currently Focusing on: **{timer_course}**")
                time.sleep(1)
            
            timer_ph.success("🎉 Sprint Finished! Great job staying focused.")
            st.session_state.xp += 10
            save_user_data()
            st.toast("Earned +10 XP for completing sprint!", icon="⭐")

    with col_trap:
        st.subheader("🧠 Distraction Trap")
        st.caption("Got a distracting urge? Log it here to clear your working memory.")
        
        distraction_input = st.text_input("Log Distraction:", key="dist_in")
        if st.button("Trap Thought"):
            if distraction_input:
                st.session_state.distractions.append({
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "thought": sanitize_string(distraction_input)
                })
                # Cap distraction array length
                st.session_state.distractions = st.session_state.distractions[-50:]
                save_user_data()
                st.toast("Thought trapped!", icon="🧠")
                st.rerun()

        if st.session_state.distractions:
            st.divider()
            st.write("Recent Trapped Thoughts:")
            for d in reversed(st.session_state.distractions[-5:]):
                st.caption(f"• **[{d['time']}]** {d['thought']}")

# -------------------------------------------------------------------
# TAB 5: VISUAL TIMELINE & GUARDRAILS
# -------------------------------------------------------------------
with tabs[4]:
    st.header("📊 Daily Visual Timeline & Health Guardrails")

    col_s, col_sch = st.columns(2)
    with col_s:
        sleep_h = st.number_input("Target Sleep Hours", min_value=4.0, max_value=12.0, value=8.0, step=0.5, key="guard_sleep")
    with col_sch:
        school_h = st.number_input("School / Class Hours", min_value=0.0, max_value=12.0, value=6.0, step=0.5, key="guard_school")

    calc_study_h = total_study_minutes_today / 60.0 if 'total_study_minutes_today' in locals() else 3.5
    free_h = max(0.0, 24.0 - sleep_h - school_h - calc_study_h)

    # Render Visual Plotly Chart
    timeline_df = pd.DataFrame([
        {"Category": "Sleep Window", "Hours": sleep_h},
        {"Category": "School / Class", "Hours": school_h},
        {"Category": "Planned Self-Study", "Hours": calc_study_h},
        {"Category": "Free / Personal Time", "Hours": free_h}
    ])
    
    # Filter out 0-hour categories for clean rendering
    timeline_df = timeline_df[timeline_df["Hours"] > 0]

    fig = px.bar(
        timeline_df, 
        x="Hours", 
        y="Category", 
        orientation='h', 
        color="Category",
        text="Hours",
        color_discrete_map={
            "Sleep Window": "#2b5c8f", 
            "School / Class": "#e67e22", 
            "Planned Self-Study": "#27ae60", 
            "Free / Personal Time": "#8e44ad"
        }
    )
    fig.update_layout(
        height=280, 
        showlegend=False, 
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(range=[0, 24], title="Hours in Day (24h Total)")
    )
    st.plotly_chart(fig, use_container_width=True)

    # Health Guardrail Alerts
    total_committed = sleep_h + school_h + calc_study_h
    if total_committed > 24.0:
        over_by = total_committed - 24.0
        st.error(f"🚨 **Overcommitment Alert:** Your planned day exceeds 24 hours by `{format_hours_and_mins(over_by * 60)}`! Reduce study or school targets to protect your sleep.")
    else:
        st.success(f"✅ **Healthy Day Balance:** You have `{format_hours_and_mins(free_h * 60)}` of unallocated free time remaining today.")
