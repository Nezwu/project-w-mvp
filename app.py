import streamlit as st
import os
from openai import OpenAI

st.set_page_config(page_title="Project W – MVP Demo", layout="centered")

st.title("Project W – MVP Demo")
st.write("Upload documents and check whether a client comment was applied.")

st.divider()

# --- OpenAI client ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found. Please set it in Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- User inputs ---
comment = st.text_area(
    "Client comment",
    placeholder="e.g. Correct 'Committe’s' to 'Committee’s'.",
    height=100
)

before_pdf = st.file_uploader(
    "Comments PDF (before)",
    type=["pdf"]
)

after_pdf = st.file_uploader(
    "Amended PDF (after)",
    type=["pdf"]
)

st.divider()

# --- Action button ---
if st.button("Check change"):
    if not comment:
        st.warning("Please enter a client comment.")
    elif not before_pdf or not after_pdf:
        st.warning("Please upload both PDFs.")
    else:
        with st.spinner("Asking AI..."):
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant helping to analyse document review comments. "
                            "For now, simply restate the user's comment and confirm you received it."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"The client comment is: {comment}",
                    },
                ],
                temperature=0.0,
            )

        st.success("AI responded successfully.")
        st.subheader("AI response (test)")
        st.write(response.choices[0].message.content)

