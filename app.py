from pypdf import PdfReader
import streamlit as st
import os
from openai import OpenAI

st.set_page_config(page_title="Project W - MVP Demo", layout="centered")

st.title("Project W - MVP Demo")
st.write("AI-powered comment verification prototype.")

st.divider()

# --- OpenAI client ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found. Please set it in Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- Inputs ---
comment = st.text_area(
    "Client Comment",
    placeholder="e.g. Correct 'Committe’s' to 'Committee’s'.",
    height=80
)

before_pdf = st.file_uploader("Comments PDF (before)", type="pdf")
after_pdf = st.file_uploader("Amended PDF (after)", type="pdf")

st.divider()

if st.button("Check Change"):

    if not comment or not before_pdf or not after_pdf:
        st.warning("Please fill in all fields.")
    else:
        with st.spinner("Analyzing with AI..."):
            before_reader = PdfReader(before_pdf)
            after_reader = PdfReader(after_pdf)

            before_text = ""
            for page in before_reader.pages:
                before_text += page.extract_text() or ""

            after_text = ""
            for page in after_reader.pages:
                after_text += page.extract_text() or ""
            
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": """
You are an expert document reviewer.

Your task is to determine whether a client comment has been applied in the amended text.

Respond ONLY in valid JSON with this format:

{
  "status": "Applied | Missed | Unclear",
  "explanation": "Short explanation of reasoning.",
  "confidence": "High | Medium | Low"
}

Rules:
- "Applied" = The requested change clearly appears in the after text.
- "Missed" = The requested change clearly does NOT appear.
- "Unclear" = Cannot confidently determine.
"""
                    },
                    {
                        "role": "user",
                        "content": f"""
Client comment:
{comment}

Before text:
{before_text}

After text:
{after_text}
"""
                    }
                ]
            )

        st.success("Analysis complete.")
        st.subheader("AI Result")
        st.code(response.choices[0].message.content, language="json")
