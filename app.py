import streamlit as st
import json
import os
import datetime
import time
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# Page Config
st.set_page_config(page_title="Smart Auto-Scheduler Pro", page_icon="⚡", layout="wide")
st.title("⚡ Smart Auto-Scheduler Pro")
st.caption("AI-Powered Study Planning, Project Deadlines, Focus Timers, and Health Guardrails")

# Helper Function: Convert total minutes into an "X hrs Y mins" string
def format_hours_and_mins(total_minutes):
    hrs = int(total_minutes // 60)
    mins = int(round(total_minutes % 60))
    if hrs == 0:
        return f"{mins} mins"
    elif mins == 0:
        return f"{hrs} hrs"
    return f"{hrs} hrs {mins} mins"

# Load Course Dataset from JSON
@st.cache_data
def load_preset_courses():
    if os.path.exists("courses.json"):
        with open("courses.json", "r") as f:
            return json.load(f)
    return {}

PRESET_COURSES = load_preset_courses()

# -------------------------------------------------------------------
# FEATURE 5: LOCAL DATA PERSISTENCE (SAVE / LOAD STATE)
# -------------------------------------------------------------------
DATA_FILE = "user_data.json"

def load_user_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"user_schedule": [], "projects": [], "distractions": []}

def save_user_data():
    data = {
        "user_schedule": st.session_state.get("user_schedule", []),
        "projects": st.session_state.get("projects", []),
        "distractions": st.session_state.get("distractions", [])
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# Initialize Session State from Storage
saved_data = load_user_data()
if "user_schedule" not in st.session_state:
    st.session_state.user_schedule = saved_data.get("user_schedule", [])
if "projects" not in st.session_state:
    st.session_state.projects = saved_data.get("projects", [])
if "distractions" not in st.session_state:
    st.session_state.distractions = saved_data.get("distractions", [])

# Sidebar Setup
st.sidebar.header("🔑 Setup")
api_key = st.sidebar.text_input("Gemini API Key (Optional)", type="password")
if api_key:
    genai.configure(api_key=api_key)

tabs = st.tabs([
    "📚 Courses & Load", 
    "📅 Daily Schedule & Deliverables", 
    "🚀 Project Engine", 
    "⏱️ Focus Timer", 
    "📊 Visual Timeline & Guardrails"
])

# -------------------------------------------------------------------
# TAB 1: COURSE SELECTION & MANAGEMENT
# -------------------------------------------------------------------
with tabs[0]:
    st.header("Course Load Configuration")
    
    level_filter = st.multiselect(
        "Filter Preset Database by Level:",
        options=["Middle School", "High School", "AP", "College"],
        default=["High School", "AP", "College"]
    )

    filtered_presets = {
        name: data for name, data in PRESET_COURSES.items() 
        if data.get("level") in level_filter
    }

    selected_presets = st.multiselect(
        "Search & Choose Courses:",
        options=list(filtered_presets.keys()),
        default=[c["course"] for c in st.session_state.user_schedule if c.get("course") in filtered_presets]
    )

    # Sync Selection
    new_schedule = []
    for course_name in selected_presets:
        data = PRESET_COURSES[course_name]
        new_schedule.append({
            "course": course_name,
            "level": data["level"],
            "difficulty": data["difficulty"],
            "hours": data["hours"],
            "reasoning": data["reasoning"]
        })
    
    # Keep custom courses that are not in presets
    for c in st.session_state.user_schedule:
        if c.get("level") == "Custom":
            new_schedule.append(c)

    if new_schedule != st.session_state.user_schedule:
        st.session_state.user_schedule = new_schedule
        save_user_data()

    # Custom Class Addition
    with st.expander("➕ Personalize or Add Custom Class"):
        custom_name = st.text_input("Custom Course Name")
        custom_syllabus = st.text_area("Syllabus / Topics")
        if st.button("Analyze & Add Custom Class"):
            if not api_key:
                st.error("API key required for custom AI analysis.")
            elif custom_name and custom_syllabus:
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Analyze syllabus for '{custom_name}': {custom_syllabus}\nRespond ONLY in raw JSON: {{\"difficulty\": <1-5>, \"recommended_weekly_hours\": <int>, \"reasoning\": \"<text>\"}}"
                    res = model.generate_content(prompt)
                    ai_data = json.loads(res.text.replace("```json", "").replace("```", "").strip())
                    
                    st.session_state.user_schedule.append({
                        "course": custom_name,
                        "level": "Custom",
                        "difficulty": ai_data["difficulty"],
                        "hours": ai_data["recommended_weekly_hours"],
                        "reasoning": ai_data["reasoning"]
                    })
                    save_user_data()
                    st.success(f"Added {custom_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Display Active Courses
    if st.session_state.user_schedule:
        st.subheader("Your Active Courses")
        for c in st.session_state.user_schedule:
            with st.expander(f"[{c['level']}] {c['course']} — Difficulty: {c['difficulty']}/5"):
                st.write(f"**Baseline Load:** ~{c['hours']} hrs/week")
                st.write(f"**Reasoning:** {c['reasoning']}")

# -------------------------------------------------------------------
# TAB 2: DAILY SCHEDULE & DELIVERABLES (FEATURE 1)
# -------------------------------------------------------------------
with tabs[1]:
    st.header("Daily Allocator & Task Deliverables")
    
    if not st.session_state.user_schedule:
        st.info("Select or add courses in Tab 1 first!")
    else:
        st.subheader("Available Study Time Today")
        col1, col2 = st.columns(2)
        with col1:
            study_hours = st.number_input("Hours", min_value=0, max_value=16, value=3, step=1, key="alloc_h")
        with col2:
            study_mins = st.number_input("Minutes", min_value=0, max_value=55, value=30, step=5, key="alloc_m")
            
        total_study_minutes_today = (study_hours * 60) + study_mins
        total_difficulty = sum(c["difficulty"] for c in st.session_state.user_schedule)

        st.divider()
        st.subheader(f"Weighted Study Breakdown ({format_hours_and_mins(total_study_minutes_today)} Total)")
        
        for c in st.session_state.user_schedule:
            allocated_minutes = (c["difficulty"] / total_difficulty) * total_study_minutes_today
            formatted_time = format_hours_and_mins(allocated_minutes)
            
            st.markdown(f"### • **[{c['level']}] {c['course']}** → `{formatted_time}`")
            # Feature 1: Deliverable Input
            deliverable_key = f"deliverable_{c['course']}"
            default_val = st.session_state.get(deliverable_key, "")
            task = st.text_input(f"Target deliverable for {c['course']} today:", value=default_val, placeholder="e.g., Read Ch. 4, Solve problems 1-10", key=deliverable_key)

# -------------------------------------------------------------------
# TAB 3: PROJECT DEADLINE ENGINE (FEATURE 3)
# -------------------------------------------------------------------
with tabs[2]:
    st.header("🚀 Project & Assignment Engine")
    st.write("Track upcoming projects and let the app distribute daily workload requirements automatically.")

    with st.form("add_project_form"):
        p_name = st.text_input("Project / Assignment Title")
        p_hours = st.number_input("Estimated Total Hours Needed", min_value=1.0, max_value=50.0, value=5.0, step=0.5)
        p_deadline = st.date_input("Due Date", min_value=datetime.date.today())
        if st.form_submit_button("Add Project"):
            st.session_state.projects.append({
                "title": p_name,
                "total_hours": p_hours,
                "deadline": str(p_deadline)
            })
            save_user_data()
            st.success(f"Project '{p_name}' added!")
            st.rerun()

    if st.session_state.projects:
        st.subheader("Active Projects & Daily Requirements")
        updated_projects = []
        for i, p in enumerate(st.session_state.projects):
            due_date = datetime.datetime.strptime(p["deadline"], "%Y-%m-%d").date()
            days_remaining = max(1, (due_date - datetime.date.today()).days)
            daily_needed_mins = (p["total_hours"] * 60) / days_remaining
            
            col_p1, col_p2 = st.columns([3, 1])
            with col_p1:
                st.write(f"**{p['title']}** | Due: {p['deadline']} ({days_remaining} days left)")
                st.write(f"👉 **Required Work Today:** `{format_hours_and_mins(daily_needed_mins)}` / day to finish on time")
            with col_p2:
                if st.button("Delete / Complete", key=f"del_proj_{i}"):
                    continue
            updated_projects.append(p)
            st.divider()

        if len(updated_projects) != len(st.session_state.projects):
            st.session_state.projects = updated_projects
            save_user_data()
            st.rerun()

# -------------------------------------------------------------------
# TAB 4: LIVE FOCUS TIMER & DISTRACTION TRAP (FEATURE 2)
# -------------------------------------------------------------------
with tabs[3]:
    st.header("⏱️ Active Focus Session & Pomodoro")
    
    col_timer, col_distract = st.columns([2, 1])
    
    with col_timer:
        st.subheader("Start Study Sprint")
        timer_course = st.selectbox("Select Course for Session", [c["course"] for c in st.session_state.user_schedule] if st.session_state.user_schedule else ["General Focus"])
        timer_minutes = st.number_input("Sprint Minutes", min_value=5, max_value=120, value=25, step=5)
        
        if st.button("▶️ Start Focus Timer"):
            ph = st.empty()
            total_seconds = int(timer_minutes * 60)
            while total_seconds > 0:
                mins, secs = divmod(total_seconds, 60)
                ph.header(f"⏳ **{mins:02d}:{secs:02d}** — Focus on {timer_course}")
                time.sleep(1)
                total_seconds -= 1
            ph.success("🎉 Sprint Complete! Take a break.")

    with col_distract:
        st.subheader("🧠 Distraction Trap Log")
        st.caption("Got an urge to check your phone or do something else? Log it here to clear your brain without stopping.")
        
        distraction_text = st.text_input("Log Distracted Thought:", key="dist_input")
        if st.button("Trap Thought"):
            if distraction_text:
                st.session_state.distractions.append({
                    "time": datetime.datetime.now().strftime("%H:%M"),
                    "thought": distraction_text
                })
                save_user_data()
                st.rerun()
                
        if st.session_state.distractions:
            for d in reversed(st.session_state.distractions[-5:]):
                st.caption(f"• **[{d['time']}]** {d['thought']}")

# -------------------------------------------------------------------
# TAB 5: VISUAL TIMELINE & HEALTH GUARDRAILS (FEATURE 4)
# -------------------------------------------------------------------
with tabs[4]:
    st.header("📊 Visual Schedule & Guardrails")

    col_sleep, col_school = st.columns(2)
    with col_sleep:
        sleep_h = st.number_input("Target Sleep Hours", min_value=4, max_value=12, value=8, step=1, key="v_sh")
    with col_school:
        school_h = st.number_input("In-Class / School Hours", min_value=0, max_value=12, value=6, step=1, key="v_sch_h")

    study_h = total_study_minutes_today / 60 if 'total_study_minutes_today' in locals() else 3.5
    free_h = max(0.0, 24.0 - sleep_h - school_h - study_h)

    st.subheader("24-Hour Time Distribution")
    
    # Feature 4: Plotly Visual Timeline Chart
    timeline_data = pd.DataFrame([
        {"Category": "Sleep", "Hours": sleep_h},
        {"Category": "School", "Hours": school_h},
        {"Category": "Self-Study", "Hours": study_h},
        {"Category": "Free / Personal", "Hours": free_h}
    ])
    
    fig = px.bar(
        timeline_data, 
        x="Hours", 
        y="Category", 
        orientation='h', 
        color="Category",
        color_discrete_map={
            "Sleep": "#1f77b4", 
            "School": "#ff7f0e", 
            "Self-Study": "#2ca02c", 
            "Free / Personal": "#9467bd"
        },
        text="Hours"
    )
    fig.update_layout(height=300, showlegend=False, xaxis=dict(range=[0, 24]))
    st.plotly_chart(fig, use_container_width=True)

    if 24.0 - sleep_h - school_h - study_h < 0:
        st.error("🚨 Overcommitment Alert: Your combined commitments exceed 24 hours! Reduce study or project hours to preserve sleep.")
    else:
        st.success(f"✅ Healthy Schedule: You have {free_h:.1f} hours left over today for relaxation and rest.")
