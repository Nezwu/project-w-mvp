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


# --- Helper functions ---
def extract_pages(pdf_file):
    """
    Extract text from a PDF page by page.

    Returns:
        list[dict]: [
            {"page_number": 1, "text": "..."},
            {"page_number": 2, "text": "..."},
            ...
        ]
    """
    reader = PdfReader(pdf_file)
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({
            "page_number": i + 1,
            "text": text.strip()
        })

    return pages


def combine_pages_to_text(pages):
    """
    Combine page-level text back into one large string.
    This keeps your current AI workflow working for now,
    while also letting us inspect pages individually.
    """
    combined_text = []

    for page in pages:
        combined_text.append(
            f"\n--- PAGE {page['page_number']} ---\n{page['text']}"
        )

    return "\n".join(combined_text)


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
        with st.spinner("Extracting PDF text page by page..."):
            before_pages = extract_pages(before_pdf)
            after_pages = extract_pages(after_pdf)

            before_text = combine_pages_to_text(before_pages)
            after_text = combine_pages_to_text(after_pages)

        st.success("PDF extraction complete.")

        # --- Debug / verification section ---
        st.subheader("Extraction Summary")
        st.write(f"Before PDF pages: {len(before_pages)}")
        st.write(f"After PDF pages: {len(after_pages)}")

        with st.expander("Preview extracted pages - Before PDF"):
            preview_count = min(5, len(before_pages))
            for page in before_pages[:preview_count]:
                st.markdown(f"**Page {page['page_number']}**")
                if page["text"]:
                    st.text(page["text"][:1500])
                else:
                    st.text("[No text extracted]")
                st.divider()

        with st.expander("Preview extracted pages - After PDF"):
            preview_count = min(5, len(after_pages))
            for page in after_pages[:preview_count]:
                st.markdown(f"**Page {page['page_number']}**")
                if page["text"]:
                    st.text(page["text"][:1500])
                else:
                    st.text("[No text extracted]")
                st.divider()

        with st.spinner("Analyzing with AI..."):
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
