from pypdf import PdfReader
import streamlit as st
import os
import re
from openai import OpenAI

st.set_page_config(page_title="Project W - MVP Demo", layout="centered")

st.title("Project W - MVP Demo")
st.write("AI-powered comment verification prototype.")

st.divider()

# --- Configuration ---
SMALL_DOC_PAGE_THRESHOLD = 5
MAX_FALLBACK_PAGES = 5
TOP_CANDIDATE_PAGES = 3

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
    - convert curly apostrophes / quotes
    - remove extra spaces
    - remove most punctuation except apostrophes, quotes, ampersand, hyphen
    """
    text = text.lower()
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9\s'\"&-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_keywords(comment):
    """
    Extract context-aware keywords from the client comment.
    """
    stop_words = {
        "the", "and", "for", "that", "this", "with", "from", "into", "have",
        "has", "had", "was", "were", "are", "is", "be", "been", "being",
        "to", "of", "in", "on", "at", "by", "or", "as", "an", "a",
        "correct", "change", "replace", "revise", "amend", "update",
        "please", "kindly", "should", "make", "it", "its", "it's",
        "word", "words", "text", "phrase", "heading", "title", "line",
        "page", "para", "paragraph", "section"
    }

    normalized_comment = normalize_text(comment)

    quoted_phrases = re.findall(r'"([^"]+)"', normalized_comment)
    words = re.findall(r"\b[\w'&-]+\b", normalized_comment)

    keywords = []

    for phrase in quoted_phrases:
        phrase = phrase.strip()
        if len(phrase) >= 3:
            keywords.append(phrase)

    for word in words:
        if len(word) >= 3 and word not in stop_words:
            keywords.append(word)

    unique_keywords = []
    seen = set()
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords


def score_page(page_text, keywords):
    """
    Score a page based on keyword matches.
    Longer keywords/phrases get more weight.
    """
    normalized_page = normalize_text(page_text)
    score = 0

    for keyword in keywords:
        occurrences = normalized_page.count(keyword)

        if " " in keyword:
            score += occurrences * 5
        elif len(keyword) >= 8:
            score += occurrences * 3
        elif len(keyword) >= 5:
            score += occurrences * 2
        else:
            score += occurrences

    return score


def find_candidate_pages(pages, keywords, top_n=TOP_CANDIDATE_PAGES):
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


def build_fallback_pages(pages, max_pages=MAX_FALLBACK_PAGES):
    """
    Build fallback pages safely.
    - For small documents, use all pages.
    - For larger documents, cap the number of pages sent to AI.
    """
    if len(pages) <= SMALL_DOC_PAGE_THRESHOLD:
        fallback_source = pages
        fallback_mode = f"all pages used (small document: {len(pages)} pages)"
    else:
        fallback_source = pages[:max_pages]
        fallback_mode = f"first {len(fallback_source)} pages used (large document fallback capped)"

    fallback_pages = [
        {
            "page_number": page["page_number"],
            "text": page["text"],
            "score": 0
        }
        for page in fallback_source
    ]

    return fallback_pages, fallback_mode


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
    placeholder='e.g. In the heading "Audit and Risk Management Committe’s Statement", correct "Committe’s" to "Committee’s".',
    height=100
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

        before_candidates = find_candidate_pages(before_pages, keywords, top_n=TOP_CANDIDATE_PAGES)
        after_candidates = find_candidate_pages(after_pages, keywords, top_n=TOP_CANDIDATE_PAGES)

        before_fallback_used = False
        after_fallback_used = False
        before_fallback_mode = ""
        after_fallback_mode = ""

        if not before_candidates:
            before_candidates, before_fallback_mode = build_fallback_pages(before_pages)
            before_fallback_used = True

        if not after_candidates:
            after_candidates, after_fallback_mode = build_fallback_pages(after_pages)
            after_fallback_used = True

        before_text = combine_selected_pages(before_candidates)
        after_text = combine_selected_pages(after_candidates)

        st.success("PDF extraction and page filtering complete.")

        st.subheader("Filtering Summary")
        st.write(f"Before PDF pages: {len(before_pages)}")
        st.write(f"After PDF pages: {len(after_pages)}")
        st.write(f"Extracted keywords: {keywords if keywords else '[None]'}")
        st.write(f"Top candidate page limit: {TOP_CANDIDATE_PAGES}")
        st.write(f"Fallback page cap for large documents: {MAX_FALLBACK_PAGES}")

        if before_fallback_used:
            st.write(f"Before PDF fallback used: Yes — {before_fallback_mode}")
        else:
            st.write("Before PDF fallback used: No")

        if after_fallback_used:
            st.write(f"After PDF fallback used: Yes — {after_fallback_mode}")
        else:
            st.write("After PDF fallback used: No")

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