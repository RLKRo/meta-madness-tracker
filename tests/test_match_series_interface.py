from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import pytest

from app.match_series_interface import MatchSeriesManager, _mapper_registry


@pytest.fixture()
def pre_bans():
    yield {"q1": set(), "q2": {"anduin", "blaze"}, "q3": {"brightwing", "deathwing"}}


@pytest.fixture()
def session():
    engine = create_engine("sqlite://", echo=True)

    _mapper_registry.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture()
def match_series_list(pre_bans, session):
    yield [
        MatchSeriesManager.create_new(session, name, pre_banned_heroes)
        for name, pre_banned_heroes in pre_bans.items()
    ]


def test_just_works(pre_bans, session, match_series_list):
    for index, match_series in enumerate(pre_bans.items()):
        manager = MatchSeriesManager(session, match_series_list[index].id)

        assert manager.match_series.name == match_series[0]
        assert set(manager.match_series.banned_heroes) == match_series[1]


def test_unique_edit_keys(pre_bans, session, match_series_list):
    assert len({match.edit_key for match in match_series_list}) == 3


def test_raise_on_unlawful_edit_attempt(pre_bans, session, match_series_list):
    for index, match_series in enumerate(pre_bans.items()):
        manager = MatchSeriesManager(session, match_series_list[index].id)

        with pytest.raises(RuntimeError):
            manager.set_hero_bans(["anduin", "qhira"], [])
        assert set(manager.match_series.banned_heroes) == match_series[1]

    for index, match_series in enumerate(pre_bans.items()):
        manager = MatchSeriesManager(session, match_series_list[index].id, "wrong_key")

        with pytest.raises(RuntimeError):
            manager.set_hero_bans([], ["anduin", "qhira"])
        assert set(manager.match_series.banned_heroes) == match_series[1]


def test_bans(pre_bans, session, match_series_list):
    manager = MatchSeriesManager(
        session, match_series_list[0].id, match_series_list[0].edit_key
    )

    manager.set_hero_bans(["rexxar"], [])
    assert set(manager.match_series.banned_heroes) == {"rexxar"}

    new_manager = MatchSeriesManager(session, match_series_list[0].id)
    assert set(new_manager.match_series.banned_heroes) == {"rexxar"}

    # test with existing bans
    manager = MatchSeriesManager(
        session, match_series_list[1].id, match_series_list[1].edit_key
    )

    manager.set_hero_bans(["anduin", "probius"], [])
    assert set(manager.match_series.banned_heroes) == {"anduin", "probius", "blaze"}


def test_unbans(pre_bans, session, match_series_list):
    manager = MatchSeriesManager(
        session, match_series_list[2].id, match_series_list[2].edit_key
    )

    manager.set_hero_bans([], ["brightwing", "blaze"])
    assert set(manager.match_series.banned_heroes) == {"deathwing"}

    manager = MatchSeriesManager(
        session, match_series_list[2].id, match_series_list[2].edit_key
    )

    manager.set_hero_bans([], [])
    assert set(manager.match_series.banned_heroes) == {"deathwing"}


def test_bans_unbans(pre_bans, session, match_series_list):
    manager = MatchSeriesManager(
        session, match_series_list[2].id, match_series_list[2].edit_key
    )

    manager.set_hero_bans(["brightwing", "anduin"], ["brightwing", "blaze"])
    assert set(manager.match_series.banned_heroes) == {"deathwing", "anduin"}

    manager = MatchSeriesManager(
        session, match_series_list[2].id, match_series_list[2].edit_key
    )

    manager.set_hero_bans(["deathwing"], ["deathwing"])
    assert set(manager.match_series.banned_heroes) == {"anduin"}


def test_cho_gall(pre_bans, session, match_series_list):
    manager = MatchSeriesManager(
        session, match_series_list[2].id, match_series_list[2].edit_key
    )

    manager.set_hero_bans(["cho"], [])
    assert set(manager.match_series.banned_heroes) == {"deathwing", "brightwing", "cho", "gall"}

    manager.set_hero_bans(["blaze"], ["gall"])
    assert set(manager.match_series.banned_heroes) == {"deathwing", "brightwing", "blaze"}

    manager.set_hero_bans(["cho", "gall"], [])
    assert set(manager.match_series.banned_heroes) == {"deathwing", "brightwing", "cho", "gall", "blaze"}

    manager.set_hero_bans(["anduin"], ["cho", "gall"])
    assert set(manager.match_series.banned_heroes) == {"deathwing", "brightwing", "blaze", "anduin"}
