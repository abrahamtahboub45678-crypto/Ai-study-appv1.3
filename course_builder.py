import json
import google.generativeai as genai

def generate_full_course(course_topic, duration_description, api_key):
    """
    Generates a complete dynamic course structure including 
    assignments, quizzes, essays, and projects via Gemini AI.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert university professor. Create a complete, structured course for:
    - Topic: {course_topic}
    - Duration: {duration_description}

    Output STRICTLY raw JSON matching this schema (no markdown formatting, no commentary):
    {{
      "course_title": "{course_topic}",
      "duration": "{duration_description}",
      "description": "Short overview of the course.",
      "weeks": [
        {{
          "week_number": 1,
          "topic": "Week Topic Title",
          "lessons": ["Lesson 1", "Lesson 2"],
          "assignment": {{
            "title": "Assignment Title",
            "instructions": "Detailed task instructions..."
          }},
          "quiz": {{
            "title": "Weekly Assessment",
            "questions": [
              {{
                "question": "Question text?",
                "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                "answer": "A) Option 1"
              }}
            ]
          }},
          "essay_prompt": "Essay prompt for the week...",
          "project": "Hands-on project deliverable..."
        }}
      ]
    }}
    """
    
    response = model.generate_content(prompt)
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)
