import streamlit as st

st.set_page_config(page_title="Project W – MVP Demo", layout="centered")

st.title("Project W – MVP Demo")
st.write("Upload documents and check whether a client comment was applied.")

st.divider()

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
        st.success("Inputs received. (AI check will be added next.)")
        st.write("Comment:")
        st.code(comment)
        st.write("Before PDF:", before_pdf.name)
        st.write("After PDF:", after_pdf.name)
