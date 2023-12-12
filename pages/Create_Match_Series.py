from datetime import datetime, timedelta

import streamlit as st

from app import HEROES_DICT, clean_hero_name, MatchSeriesManager, db_connection


st.set_page_config(
    page_title="Meta Madness Tracker",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ERROR_MESSAGE = (
    "Some of the hero names could not be recognized:",
    "See full list of heroes at https://heroesofthestorm.blizzard.com/en-us/heroes/.",
)

SPAM_MESSAGE = "Please wait. You can only create a match series once every minute."

SPAM_DELTA = timedelta(minutes=1)

st.experimental_set_query_params()

if "match_series_data" not in st.session_state:
    st.session_state["match_series_data"] = None

form = st.form("new_match_series")

form.write("Create new match series")

name = form.text_input(
    "Name", placeholder="ASH vs. Raiders", max_chars=50, key="series_name"
)


def _parse_pre_banned_heroes(text: str):
    parsed_hero_names = [
        (line, clean_hero_name(line)) for line in text.split("\n") if line
    ]

    incorrect_names = [
        name[0] for name in parsed_hero_names if name[1] not in HEROES_DICT
    ]

    return parsed_hero_names, incorrect_names


def on_pre_banned_heroes():
    parsed_hero_names, incorrect_names = _parse_pre_banned_heroes(
        st.session_state["series_pre_banned"]
    )

    if len(incorrect_names) == 0:
        if "last_game_created_at" in st.session_state:
            if datetime.now() - st.session_state["last_game_created_at"] < SPAM_DELTA:
                st.session_state["match_series_data"] = SPAM_MESSAGE
                return
        st.session_state["last_game_created_at"] = datetime.now()
        st.session_state["match_series_data"] = {
            "name": st.session_state["series_name"],
            "pre_banned_heroes": {hero_name[1] for hero_name in parsed_hero_names},
        }
        st.session_state["series_pre_banned"] = ""
        st.session_state["series_name"] = ""
    else:
        st.session_state["match_series_data"] = "\n\n".join(
            [ERROR_MESSAGE[0], *incorrect_names, ERROR_MESSAGE[1]]
        )


bans = form.text_area(
    "Pre-banned heroes",
    placeholder="cho\nLi-Ming\nmalganis\nsgt hammer\nKel'Thuzad\nLt. Morales",
    help="New-line separated list of hero names. Hero names can be capitalized and contain any non-letter symbols.",
    height=200,
    key="series_pre_banned",
)

submit = form.form_submit_button(on_click=on_pre_banned_heroes)


if submit:
    match_series_data = st.session_state["match_series_data"]
    if isinstance(match_series_data, dict):
        with db_connection() as session:
            match_series = MatchSeriesManager.create_new(
                session,
                match_series_data["name"],
                match_series_data["pre_banned_heroes"],
            )
            st.success(
                f"Success! Number of banned heroes: {len(match_series.banned_heroes)}."
            )

            st.markdown(
                f"[Edit Link](/View_Match_Series?id={match_series.id}&edit_key={match_series.edit_key})"
                f" &mdash; this link allows to view and edit bans."
            )

            st.markdown(
                f"[View Link](/View_Match_Series?id={match_series.id})"
                f" &mdash; this link allows to view bans."
            )
    elif isinstance(match_series_data, str):
        st.warning(match_series_data)
    else:
        st.error("Something went wrong, please reload the page and submit an issue.")
