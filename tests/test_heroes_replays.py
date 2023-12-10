from pathlib import Path
import os

import pytest

from app.heroes import get_archive_protocol, extract_heroes_from_details, extract_heroes_from_tracker_events

REPLAY_DIR = Path(os.getenv("REPLAY_DIR"))


def get_replay_details(replay):
    with get_archive_protocol(replay) as (archive, protocol):
        contents = archive.header['user_data_header']['content']
        header = protocol.decode_replay_header(contents)

        contents = archive.read_file('replay.details')
        details = protocol.decode_replay_details(contents)

        replay_details = {
            "elapsed_game_loops": header.get("m_elapsedGameLoops"),
            "title": details.get("m_title").decode()
        }

        return replay_details


@pytest.mark.parametrize(
    "replay", list(map(str, REPLAY_DIR.iterdir()))
)
class TestReplayExtractorFunctions:
    def test_heroes_extraction_from_details(self, replay):
        with get_archive_protocol(replay) as (archive, protocol):

            heroes_details = extract_heroes_from_details(archive, protocol, False)

            pytest.shared.setdefault(replay, {})["details"] = heroes_details

            assert len(heroes_details) == 10, print(heroes_details, get_replay_details(replay))

            return heroes_details

    def test_heroes_extraction_from_tracker_events(self, replay):
        with get_archive_protocol(replay) as (archive, protocol):

            heroes_details = extract_heroes_from_tracker_events(archive, protocol, False)

            pytest.shared.setdefault(replay, {})["tracker_events"] = heroes_details

            assert len(heroes_details) == 10, print(heroes_details, get_replay_details(replay))

            return heroes_details

    def test_hero_sets_equal(self, replay):
        if "tracker_events" not in pytest.shared.get(replay, {}):
            try:
                self.test_heroes_extraction_from_tracker_events(replay)
            except AssertionError:
                pass
        if "details" not in pytest.shared.get(replay, {}):
            try:
                self.test_heroes_extraction_from_details(replay)
            except AssertionError:
                pass
        assert sorted(pytest.shared[replay]["details"]) == sorted(pytest.shared[replay]["tracker_events"]), print(get_replay_details(replay))