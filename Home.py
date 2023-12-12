import streamlit as st

from app.common import align_headers

st.set_page_config(
    page_title="Meta Madness Tracker",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.experimental_set_query_params()

with open("README.md", "r") as fd:
    st.markdown(
        fd.read().replace("https://meta-madness-tracker.streamlit.app", "")
    )  # use relative links
align_headers()
