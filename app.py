import streamlit as st

st.set_page_config(page_title="Project W – MVP Demo", layout="centered")

st.title("Project W – MVP Demo")
st.write("Welcome, Woon. This is your first live version of Project W.")

st.markdown("""
### What this demo will do (very soon)

- Let you upload a **Comments PDF** and an **Amended PDF**
- Enter a **client comment** (e.g. “Correct 'Committe’s' to 'Committee’s'.”)
- Ask AI if the change has been **Applied**, **Missed**, or is **Unclear**

Right now, this is just a placeholder to prove deployment is working.
""")
