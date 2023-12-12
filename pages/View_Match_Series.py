import streamlit as st
from st_keyup import st_keyup
from sqlalchemy.exc import NoResultFound

from app import (
    extract_heroes_from_replay,
    HEROES_DICT,
    HERO_ROLES,
    clean_hero_name,
    MatchSeriesManager,
    align_headers,
    db_connection,
)

st.set_page_config(
    page_title="Meta Madness Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)


def image_with_tooltip(img, tooltip, ban: bool = False, filtered: bool = False):
    """
    Return HTML image with a tooltip and an optional ban cross.

    :param img: Image source.
    :param tooltip: Tooltip text.
    :param ban: Whether to add a ban cross.
    :param filtered: Whether this image should have `filtered` class.
    """
    ban_image = (
        '<img class= "image ban" src="app/static/ban.png" alt="ban image">'
        if ban
        else ""
    )

    image_hover = (
        f'<div class="hoverable{" filtered" if filtered else ""}">'
        f'<img class="image" src="{img}" alt="{tooltip}">'
        + ban_image
        + f'<div class="tooltip">{tooltip.replace("-", " ")}</div>'
        '</div>'
    )

    return image_hover


def view_match_series(manager: MatchSeriesManager):
    """
    Show match series view for a match series defined by `manager`.
    """
    match_series = manager.match_series
    banned_heroes = match_series.banned_heroes
    edit_permission = manager.edit_permission

    filters = st.columns(3)

    with filters[0]:
        ban_filter = st.select_slider(
            "Which heroes to display",
            ["Banned Only", "All", "Available Only"],
            value="All",
        )
        if ban_filter == "Banned Only":
            display_cross_over_banned = st.checkbox(
                "Cross out banned heroes", value=False, help="Cross out all heroes"
            )

    with filters[1]:
        role_filter = st.multiselect("Filter by role", HERO_ROLES)

        image_width = st.slider("Icon size", min_value=60, max_value=152, value=90)

    with filters[2]:
        name_filter = st_keyup("Filter by name")

        grey_out_filtered = st.checkbox(
            "Grey out filtered heroes",
            value=True,
            help="Heroes filtered out by role and name filters will be greyed out instead of removed",
        )

    st.sidebar.title("Configuration")

    hide_filters = st.sidebar.checkbox(
        "Hide filters", value=False, help="Hide all filters above the match series name"
    )

    if edit_permission:
        st.sidebar.title("Edit Bans")
        form = st.sidebar.form("upload_form", clear_on_submit=True)

        def process_uploaded_files():
            heroes_to_ban = set()
            heroes_to_unban = set()

            uploaded_files = st.session_state["file_uploader"]
            for file in uploaded_files:
                hero_list = extract_heroes_from_replay(file)
                if isinstance(hero_list, str):
                    form.error(hero_list)
                    return
                else:
                    heroes_to_ban.update(hero_list)
            heroes_to_ban.update(st.session_state["ban_heroes"])
            heroes_to_unban.update(st.session_state["unban_heroes"])
            manager.set_hero_bans(heroes_to_ban, heroes_to_unban)

        form.file_uploader(
            "Upload replay(s) to ban heroes from",
            accept_multiple_files=True,
            type="StormReplay",
            key="file_uploader",
        )
        form.write("Manual Edits")
        form.multiselect(
            "Choose heroes to ban",
            options=set(HEROES_DICT.keys()) - banned_heroes,
            help="Choose heroes to ban in addition to the heroes from the replay(s)",
            key="ban_heroes",
        )
        form.multiselect(
            "Choose heroes to unban",
            options=banned_heroes,
            help="Choose heroes to unban",
            key="unban_heroes",
        )
        form.form_submit_button("Submit", on_click=process_uploaded_files)

    def display_heroes():
        unfiltered_images = ""
        filtered_images = ""

        for hero_name, hero in HEROES_DICT.items():
            filtered = False

            clean_filter = clean_hero_name(name_filter)
            if role_filter and hero["role"] not in role_filter:
                filtered = True
            if ban_filter == "Banned Only" and hero_name not in banned_heroes:
                continue
            if ban_filter == "Available Only" and hero_name in banned_heroes:
                continue
            if (
                name_filter
                and not (
                    hero_name.startswith(clean_filter)  # catches 'azmo' in 'azmodan'
                    or any(
                        name_part.startswith(clean_filter)
                        for name_part in hero["name"].split("-")
                    )  # catches 'ham' in 'sgt-hammer'; also assume no one would want to search for "lost v"
                )
            ):
                filtered = True

            add_cross = hero_name in banned_heroes
            if ban_filter == "Banned Only" and not display_cross_over_banned:
                add_cross = False

            image = image_with_tooltip(
                f"app/static/{hero['name']}.png", hero["name"], add_cross, filtered
            )

            if filtered:
                filtered_images += image
            else:
                unfiltered_images += image
        html_image_list = (
            '<div class="heroes">' + unfiltered_images + filtered_images + "</div>"
        )

        st.write(html_image_list, unsafe_allow_html=True)

    st.title(match_series.name, anchor="name")
    st.title(f"Banned Heroes Count: {len(banned_heroes)}", anchor="banned-hero-count")

    display_heroes()

    #############################
    # STYLING
    #############################

    align_headers()

    hide_filters_style = 'div[data-testid="stHorizontalBlock"]{display: none;}'

    if grey_out_filtered:
        grey_out_filtered_style = """
.filtered {
    opacity: 0.3;
}
"""
    else:
        grey_out_filtered_style = """
.filtered {
    display: none;
}
"""

    heroes_style = f"""
.heroes {{
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
}}
.hoverable {{
    display: flex;
    float: left;
    position: relative;
    margin: 6px;
    width: {image_width}px;
}}
.hoverable .image {{
    width: {image_width}px;
    border-width: 3px;
    border-style: solid;
    border-color: black;
}}
.hoverable .ban {{
    position: absolute;
    margin-top: -100px;
    margin-left: -100px;
    top: 100px;
    left: 100px;
    opacity: 0.8;
}}
.hoverable .tooltip {{
    opacity: 0;
    position: absolute;
    margin-top: -100px;
    margin-left: -100px;
    top: 100px;
    left: 100px;
    transition: opacity 0.5s;
    background-color: rgba(0, 0, 0, 0.8);
    color: #fff;
    font-size: 18px;
    text-align: center;
}}
.hoverable:hover .tooltip {{
    opacity: 1;
}}
"""
    hide_image_button_style = """
button[title="View fullscreen"]{
    visibility: hidden;
}
"""

    style = f"""
<style>
{hide_filters_style if hide_filters else ""}
{hide_image_button_style}
{heroes_style}
{grey_out_filtered_style}
</style>
"""

    st.write(style, unsafe_allow_html=True)


query_params = st.experimental_get_query_params()

if "id" in query_params:
    edit_keys = query_params.get("edit_key", [])
    if len(edit_keys) > 0:
        edit_key = edit_keys[-1]
    else:
        edit_key = None
    with db_connection() as session:
        try:
            match_series_manager = MatchSeriesManager(
                session, query_params["id"][-1], edit_key
            )

            view_match_series(match_series_manager)
        except NoResultFound:
            st.error("Could not find a match series with that id.")
else:
    st.info("You need a link with series ID in order to view it.")
