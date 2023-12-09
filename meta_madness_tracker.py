from itertools import islice
import json
import re

import streamlit as st
from st_keyup import st_keyup
from heroprotocol.versions import build, latest
import mpyq

st.set_page_config(
    page_title="Meta Madness Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "banned" not in st.session_state:
    st.session_state["banned"] = "# Pre-banned\n"


# itertools.batched was only introduced in 3.12
def batched(iterable, n):
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


with open("heroes.json", "r") as fd:
    heroes_json = json.load(fd)


roles = set([hero['role'] for hero in heroes_json])
pattern = r'[^A-Za-z0-9]+'


def clean_hero_name(name: str):
    return re.sub(pattern, '', name).lower()


hero_names = set([clean_hero_name(hero['name']) for hero in heroes_json])


def patch_names(name: str):
    if name == "lcio":
        return "lucio"
    return name


def get_hero_list(replay):
    archive = mpyq.MPQArchive(replay)

    contents = archive.header['user_data_header']['content']
    header = latest().decode_replay_header(contents)

    baseBuild = header['m_version']['m_baseBuild']

    try:
        protocol = build(baseBuild)
    except Exception as exc:
        return exc

    contents = archive.read_file('replay.details')
    details = protocol.decode_replay_details(contents)

    return [
        patch_names(clean_hero_name(player['m_hero'].decode())) for player in details['m_playerList']
    ]


for hero in heroes_json:
    hero['clean_name'] = clean_hero_name(hero['name'])


def image_with_tooltip(img, tooltip, ban):
    # Define the html for each image
    ban_image = '<img class= "image ban" src="app/static/ban.png" alt="ban image">' if ban else ''

    image_hover = (
        '<div class="hoverable">'
        f'<img class="image" src="{img}" alt="{tooltip}">' +
        ban_image +
        f'<div class="tooltip">{tooltip.replace("-", " ")}</div>'
        '</div>'
    )

    # Write the dynamic HTML and CSS to the content container
    return image_hover


filters = st.columns(3)

with filters[0]:
    ban_filter = st.select_slider(
        "Which heroes to display",
        ["Banned Only", "All", "Available Only"],
        value="All",
    )
    if ban_filter == "Banned Only":
        display_cross_over_banned = st.checkbox("Cross out banned heroes", value=False)

with filters[1]:
    role_filter = st.multiselect(
        "Filter by role",
        roles
    )

    image_width = st.slider("Image width", min_value=30, max_value=152, value=90)
    # image_width = 90

with filters[2]:
    name_filter = st_keyup("Filter by name")


with st.sidebar:
    st.title("Configuration")

    hide_filters = st.checkbox("Hide filters", value=False)

    st.session_state["banned"] = st.text_area("Banned heroes", height=400, value=st.session_state["banned"])

    def process_uploaded_files():
        uploaded_files = st.session_state["file_uploader"]
        for file in uploaded_files:
            hero_list = get_hero_list(file)
            if isinstance(hero_list, Exception):
                st.error(hero_list)
            st.session_state["banned"] += "\n".join(["# Game", *hero_list, ""])

    with st.form("upload_form", clear_on_submit=True):
        st.file_uploader(
            "Upload replay(s) to ban heroes", accept_multiple_files=True, type="StormReplay", key="file_uploader"
        )
        st.form_submit_button("Submit", on_click=process_uploaded_files)


banned_heroes = set(clean_hero_name(line) for line in st.session_state["banned"].split("\n") if line and line in hero_names)

if "cho" in banned_heroes or "gall" in banned_heroes:
    banned_heroes.add("cho")
    banned_heroes.add("gall")


def display_heroes():
    html_image_list = '<div class="heroes">'
    for hero in heroes_json:
        clean_filter = clean_hero_name(name_filter)
        if role_filter and hero['role'] not in role_filter:
            continue
        if ban_filter == "Banned Only" and hero['clean_name'] not in banned_heroes:
            continue
        if ban_filter == "Available Only" and hero['clean_name'] in banned_heroes:
            continue
        if name_filter and not (
                hero['clean_name'].startswith(clean_filter) or  # catches 'azmo' in 'azmodan'
                any(name_part.startswith(clean_filter) for name_part in hero['name'].split('-'))  # catches 'ham' in 'sgt-hammer'
        ):
            continue

        add_cross = hero['clean_name'] in banned_heroes
        if ban_filter == "Banned Only" and not display_cross_over_banned:
            add_cross = False

        html_image_list += image_with_tooltip(
            f"app/static/{hero['name']}.png",
            hero['name'],
            add_cross
        )
    html_image_list += f"</div>"

    st.write(html_image_list, unsafe_allow_html=True)


st.title(f"Banned Hero Count: {len(banned_heroes)}", anchor="banned-hero-count")
display_heroes()

hide_filters_style = """div[data-testid="stHorizontalBlock"]{
    display: none;
}"""

style = f'''
<style>
button[title="View fullscreen"]{{
    visibility: hidden;
}}
h1 {{
    text-align: center;
}}
{hide_filters_style if hide_filters else ""}
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
</style>
'''

st.write(style, unsafe_allow_html=True)
