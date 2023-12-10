"""
Heroes
---------
This module contains functions for everything HotS related.
It defines Hero dictionaries and functions for extracting data from replays.
"""
import json
from pathlib import Path
from typing import Dict, TypedDict
import re
from contextlib import contextmanager

from heroprotocol.versions import build, latest
import mpyq


__heroes_file_path__ = Path(__file__).parent / "heroes.json"

with open(__heroes_file_path__, "r") as __fd__:
    HEROES_DICT: Dict[
        str, TypedDict("Hero", {"name": str, "role": str, "player_spawned_name": str})
    ] = json.load(__fd__)
    "Dictionary with information about heroes in the game."

PLAYER_SPAWNED_NAMES_MAP: Dict[str, str] = {
    hero["player_spawned_name"]: hero_name for hero_name, hero in HEROES_DICT.items()
}
"Reverse mapping from PlayerSpawned values to hero names."

HERO_ROLES: set[str] = set([hero["role"] for hero in HEROES_DICT.values()])
"""A set of all the hero roles found in the config file."""

pattern = re.compile(r"[^a-z]+")


def clean_hero_name(name: str):
    """
    Standardize hero names (lower case + remove any non-letter characters).
    """
    return re.sub(pattern, "", name.lower())


def extract_heroes_from_details(archive: mpyq.MPQArchive, protocol, filter_names=True):
    """
    Extract hero list from replay details. The set only contains names included in `HEROES_DICT`.

    :param archive: First item of :py:func:`~.get_archive_protocol`.
    :param protocol: Second item of :py:func:`~.get_archive_protocol`.
    :param filter_names: Whether to return hero names not included in `HEROES_DICT`.
    """
    contents = archive.read_file("replay.details")
    details = protocol.decode_replay_details(contents)

    heroes = list()

    for player in details["m_playerList"]:
        if "m_hero" in player:
            hero_name = clean_hero_name(player["m_hero"].decode())
            if hero_name == "lcio":  # patch naming error in replays
                hero_name = "lucio"
            if not filter_names or hero_name in HEROES_DICT:
                heroes.append(hero_name)
    return heroes


def extract_heroes_from_tracker_events(
    archive: mpyq.MPQArchive, protocol, filter_names=True
):
    """
    A fallback for extracting hero list.
    Extracts data from tracker events which is slower but works for replays in any language.

    :param archive: First item of :py:func:`~.get_archive_protocol`.
    :param protocol: Second item of :py:func:`~.get_archive_protocol`.
    :param filter_names: Whether to return hero names not included in `HEROES_DICT`.
    """
    contents = archive.read_file("replay.tracker.events")
    tracker_events = protocol.decode_replay_tracker_events(contents)

    heroes = list()

    for event in tracker_events:
        if "m_eventName" in event and event["m_eventName"].decode() == "PlayerSpawned":
            hero_name = event.get("m_stringData", [{}])[-1].get("m_value")
            if hero_name is not None:
                hero_name = hero_name.decode()
            if not filter_names or hero_name in PLAYER_SPAWNED_NAMES_MAP:
                heroes.append(PLAYER_SPAWNED_NAMES_MAP[hero_name])
                if len(heroes) == 10:
                    break
    return heroes


@contextmanager
def _open_file(replay):
    if not hasattr(replay, "read"):
        with open(replay, "rb") as fd:
            yield fd
    else:
        yield replay


@contextmanager
def get_archive_protocol(replay):
    """
    Get mpyq.MPQArchive and protocol module from replay.
    :param replay: Either a file path or an object with a `read` method.
    :return:
    """
    with _open_file(replay) as fd:
        archive = mpyq.MPQArchive(fd)

        contents = archive.header["user_data_header"]["content"]
        header = latest().decode_replay_header(contents)

        base_build = header["m_version"]["m_baseBuild"]

        protocol = build(base_build)

        yield archive, protocol


def extract_heroes_from_replay(replay):
    """
    Extract heroes from a `.StormReplay` file.

    :param replay: Either a file path or an object with a `read` method.
    :return: Set of heroes that are played in the replay OR an error message if extraction was unsuccessful.
    """
    unsuccessful_extraction_message = (
        "Could not extract heroes from replay. "
        "Please open an issue on github: "
        "https://github.com/RLKRo/meta-madness-tracker/issues."
    )
    try:
        with get_archive_protocol(replay) as (archive, protocol):
            heroes = extract_heroes_from_details(archive, protocol)

            if len(heroes) == 10:
                return heroes

            heroes = extract_heroes_from_tracker_events(archive, protocol)

            if len(heroes) == 10:
                return heroes
            return unsuccessful_extraction_message
    except Exception as exc:
        return str(exc)
