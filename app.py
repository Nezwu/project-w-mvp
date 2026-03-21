from pypdf import PdfReader
import streamlit as st
import os
import re
from openai import OpenAI

st.set_page_config(page_title="Project W - MVP Demo", layout="centered")

st.title("Project W - MVP Demo")
st.write("AI-powered comment verification prototype.")

st.divider()

# --- OpenAI client ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY in the environment.")
    st.stop()

client = OpenAI(api_key=api_key)


# --- Helper functions ---
def extract_pages(pdf_file):
    reader = PdfReader(pdf_file)
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({
            "page_number": i + 1,
            "text": text.strip()
        })

    return pages


def normalize_text(text):
    """
    Normalize text for matching:
    - lowercase
    - convert curly quotes/apostrophes to straight ones
    - remove extra spaces
    - remove most punctuation except apostrophes
    """
    text = text.lower()

    # Normalize curly apostrophes / quotes
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')

    # Remove punctuation except apostrophes and quotes
    text = re.sub(r"[^a-z0-9\s'\"&-]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_keywords(comment):
    stop_words = {
        "the", "and", "for", "that", "this", "with", "from", "into", "have",
        "has", "had", "was", "were", "are", "is", "be", "been", "being",
        "to", "of", "in", "on", "at", "by", "or", "as", "an", "a",
        "correct", "change", "replace", "revise", "amend", "update",
        "please", "kindly", "should", "make", "it", "its", "it's"
    }

    normalized_comment = normalize_text(comment)
    words = re.findall(r"\b[\w']+\b", normalized_comment)

    keywords = []
    for word in words:
        if len(word) >= 3 and word not in stop_words:
            keywords.append(word)

    unique_keywords = []
    seen = set()
    for word in keywords:
        if word not in seen:
            seen.add(word)
            unique_keywords.append(word)

    return unique_keywords


def score_page(page_text, keywords):
    normalized_page = normalize_text(page_text)
    score = 0

    for keyword in keywords:
        score += normalized_page.count(keyword)

    return score


def find_candidate_pages(pages, keywords, top_n=3):
    scored_pages = []

    for page in pages:
        score = score_page(page["text"], keywords)
        scored_pages.append({
            "page_number": page["page_number"],
            "text": page["text"],
            "score": score
        })

    scored_pages.sort(key=lambda x: x["score"], reverse=True)
    top_pages = [page for page in scored_pages if page["score"] > 0][:top_n]

    return top_pages


def combine_selected_pages(pages):
    if not pages:
        return "[No relevant pages found by keyword filter]"

    combined_text = []
    for page in pages:
        combined_text.append(
            f"\n--- PAGE {page['page_number']} | SCORE {page['score']} ---\n{page['text']}"
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

        keywords = extract_keywords(comment)

        before_candidates = find_candidate_pages(before_pages, keywords, top_n=3)
        after_candidates = find_candidate_pages(after_pages, keywords, top_n=3)

        before_text = combine_selected_pages(before_candidates)
        after_text = combine_selected_pages(after_candidates)

        st.success("PDF extraction and page filtering complete.")

        st.subheader("Filtering Summary")
        st.write(f"Before PDF pages: {len(before_pages)}")
        st.write(f"After PDF pages: {len(after_pages)}")
        st.write(f"Extracted keywords: {keywords if keywords else '[None]'}")

        with st.expander("Selected candidate pages - Before PDF"):
            if before_candidates:
                for page in before_candidates:
                    st.markdown(f"**Page {page['page_number']} | Score: {page['score']}**")
                    st.text(page["text"][:1500] if page["text"] else "[No text extracted]")
                    st.divider()
            else:
                st.write("No matching pages found.")

        with st.expander("Selected candidate pages - After PDF"):
            if after_candidates:
                for page in after_candidates:
                    st.markdown(f"**Page {page['page_number']} | Score: {page['score']}**")
                    st.text(page["text"][:1500] if page["text"] else "[No text extracted]")
                    st.divider()
            else:
                st.write("No matching pages found.")

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

You will receive:
1. A client comment
2. Selected relevant pages from the before PDF
3. Selected relevant pages from the after PDF

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
- If the selected pages do not provide enough evidence, return "Unclear".
"""
                    },
                    {
                        "role": "user",
                        "content": f"""
Client comment:
{comment}

Selected pages from Before PDF:
{before_text}

Selected pages from After PDF:
{after_text}
"""
                    }
                ]
            )

        st.success("Analysis complete.")
        st.subheader("AI Result")
        st.code(response.choices[0].message.content, language="json")