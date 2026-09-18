import streamlit as st
import json
import os
import google.generativeai as genai

# Page Config
st.set_page_config(page_title="Smart Auto-Scheduler", page_icon="🤖", layout="wide")
st.title("🤖 Smart Auto-Scheduler")
st.caption("Select your courses across Middle School, High School, AP, or College. The app auto-calculates difficulty, study hours, and protects your sleep.")

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
    else:
        st.error("⚠️ 'courses.json' file not found. Make sure it is placed in the same directory as app.py.")
        return {}

PRESET_COURSES = load_preset_courses()

# Sidebar - API Key Input
st.sidebar.header("🔑 Setup")
api_key = st.sidebar.text_input("Enter Gemini API Key (Optional for Custom AI Analysis)", type="password")

if api_key:
    genai.configure(api_key=api_key)

# Session State for User's Active Schedule
if "user_schedule" not in st.session_state:
    st.session_state.user_schedule = []

tabs = st.tabs(["📚 Select / Add Courses", "📅 AI Daily Schedule", "😴 Sleep Guardrails"])

# -------------------------------------------------------------------
# TAB 1: COURSE SELECTION & LEVEL FILTERING
# -------------------------------------------------------------------
with tabs[0]:
    st.header("Select Your Current Courses")
    st.write("Filter through our extensive academic database or search for your courses.")

    # Level Filter Option
    level_filter = st.multiselect(
        "Filter Course Database by Level:",
        options=["Middle School", "High School", "AP", "College"],
        default=["High School", "AP", "College"]
    )

    # Filter preset dictionary based on selection
    filtered_presets = {
        name: data for name, data in PRESET_COURSES.items() 
        if data.get("level") in level_filter
    }

    # Preset Selection Dropdown
    selected_presets = st.multiselect(
        "Search & Choose Your Courses:",
        options=list(filtered_presets.keys()),
        default=["AP Calculus BC", "AP Physics 1"] if "AP Calculus BC" in filtered_presets else []
    )

    # Update Schedule with Presets
    current_courses = []
    for course_name in selected_presets:
        data = PRESET_COURSES[course_name]
        current_courses.append({
            "course": course_name,
            "level": data["level"],
            "difficulty": data["difficulty"],
            "hours": data["hours"],
            "reasoning": data["reasoning"]
        })

    st.divider()

    # Optional Custom Syllabus Upload / Personalization
    with st.expander("➕ Personalize or Add a Custom Class (Optional)"):
        st.write("Have a unique class or specific syllabus? Let the AI analyze it for you.")
        custom_name = st.text_input("Custom Course Name", placeholder="e.g., Honors Quantum Physics")
        custom_syllabus = st.text_area("Paste Syllabus or Course Topics", height=100)

        if st.button("🤖 Analyze & Add Custom Class"):
            if not api_key:
                st.error("Please add your Gemini API key in the sidebar to use AI for custom courses!")
            elif not custom_name or not custom_syllabus:
                st.error("Please provide both a course name and syllabus text.")
            else:
                with st.spinner("AI analyzing difficulty..."):
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"""
                        Analyze this syllabus for '{custom_name}': {custom_syllabus}
                        Respond ONLY in raw JSON format with no markdown formatting:
                        {{
                            "difficulty": <number 1 to 5>,
                            "recommended_weekly_hours": <estimated study hours per week>,
                            "reasoning": "<1 sentence explanation>"
                        }}
                        """
                        response = model.generate_content(prompt)
                        clean_text = response.text.replace("```json", "").replace("```", "").strip()
                        ai_data = json.loads(clean_text)

                        current_courses.append({
                            "course": custom_name,
                            "level": "Custom",
                            "difficulty": ai_data["difficulty"],
                            "hours": ai_data["recommended_weekly_hours"],
                            "reasoning": ai_data["reasoning"]
                        })
                        st.success(f"Added custom course '{custom_name}'!")

                    except Exception as e:
                        st.error(f"Error analyzing course: {e}")

    # Store finalized active list
    st.session_state.user_schedule = current_courses

    # Display Active Courses & Scores
    if st.session_state.user_schedule:
        st.subheader("Your Active Course Load")
        for c in st.session_state.user_schedule:
            with st.expander(f"[{c['level']}] {c['course']} — Difficulty: {c['difficulty']}/5"):
                st.write(f"**Recommended Study Share Baseline:** ~{c['hours']} hrs/week")
                st.write(f"**Why this rating:** {c['reasoning']}")

# -------------------------------------------------------------------
# TAB 2: AUTOMATIC DAILY TIME ALLOCATOR
# -------------------------------------------------------------------
with tabs[1]:
    st.header("Daily Dynamic Schedule")
    
    if not st.session_state.user_schedule:
        st.info("Select or add at least one course in Tab 1 first!")
    else:
        st.subheader("Target Study Time Today")
        col1, col2 = st.columns(2)
        with col1:
            study_hours = st.number_input("Hours", min_value=0, max_value=16, value=3, step=1)
        with col2:
            study_mins = st.number_input("Minutes", min_value=0, max_value=55, value=30, step=5)
            
        total_study_minutes_today = (study_hours * 60) + study_mins
        total_difficulty = sum(c["difficulty"] for c in st.session_state.user_schedule)

        st.divider()
        st.subheader(f"Today's Study Plan ({format_hours_and_mins(total_study_minutes_today)} Total)")
        
        for c in st.session_state.user_schedule:
            allocated_minutes = (c["difficulty"] / total_difficulty) * total_study_minutes_today
            formatted_time = format_hours_and_mins(allocated_minutes)
            
            st.write(f"• **[{c['level']}] {c['course']}** (Difficulty {c['difficulty']}/5) → **{formatted_time}** assigned today")

# -------------------------------------------------------------------
# TAB 3: SLEEP GUARDRAILS
# -------------------------------------------------------------------
with tabs[2]:
    st.header("Sleep Protection Guardrails")
    st.write("Enter your daily commitments to verify your sleep is fully protected.")

    col_sleep, col_school = st.columns(2)
    
    with col_sleep:
        st.subheader("😴 Target Sleep Window")
        sleep_h = st.number_input("Sleep Hours", min_value=4, max_value=12, value=8, step=1, key="sh")
        sleep_m = st.number_input("Sleep Minutes", min_value=0, max_value=55, value=0, step=5, key="sm")

    with col_school:
        st.subheader("🏫 In-Class / School Hours")
        school_h = st.number_input("School Hours", min_value=0, max_value=12, value=6, step=1, key="sch_h")
        school_m = st.number_input("School Minutes", min_value=0, max_value=55, value=30, step=5, key="sch_m")

    total_sleep_mins = (sleep_h * 60) + sleep_m
    total_school_mins = (school_h * 60) + school_m
    total_day_mins = 24 * 60

    used_mins = total_sleep_mins + total_school_mins
    free_mins = total_day_mins - used_mins

    st.divider()
    
    c1, c2 = st.columns(2)
    c1.metric("Protected Sleep Time", format_hours_and_mins(total_sleep_mins))
    c2.metric("Max Free Time for Study & Projects", format_hours_and_mins(free_mins))

    if free_mins < 120:
        st.error(f"🚨 Sleep Warning: You only have {format_hours_and_mins(free_mins)} free today. Scale back your study target to prevent cutting into your sleep!")
    else:
        st.success(f"✅ You have {format_hours_and_mins(free_mins)} available today while keeping your sleep schedule fully intact.")
