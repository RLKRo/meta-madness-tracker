from contextlib import contextmanager

import streamlit as st

from app.match_series_interface import _mapper_registry


def align_headers():
    """
    Centrally align text of all first level headers.
    """
    # a dirty hack but it works in this context
    style = """
    <style>
    h1 {
        text-align: center;
    }
    </style>
    """

    st.write(style, unsafe_allow_html=True)


@contextmanager
def db_connection():
    conn = st.connection("match_series", type="sql")

    with conn.session as session:
        _mapper_registry.metadata.create_all(conn.engine)

        yield session
