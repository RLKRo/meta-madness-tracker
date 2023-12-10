"""
Match Series Interface
----------------------
This module defines interface for reading match series information from sqlalchemy database.
"""
import datetime
from uuid import uuid4

from typing import Iterable, Optional

from sqlalchemy import Table, Column, Uuid, DateTime, Text, Boolean, select
from sqlalchemy.orm import registry, Session
from sqlalchemy.sql import func

from app.heroes import HEROES_DICT

_mapper_registry = registry()


def generate_uuid():
    return str(uuid4())


class MatchSeries:
    """
    Class representing a match series.

    This class also has an attribute "{hero_name}_banned" for every hero in the game.
    """

    _COLUMN_POSTFIX = "_banned"
    id: str
    created_at: datetime.datetime
    name: str
    edit_key: str
    """Key required for editing this series."""

    def _ban(self, hero: str):
        self.__setattr__(hero + self._COLUMN_POSTFIX, True)

    def _unban(self, hero: str):
        self.__setattr__(hero + self._COLUMN_POSTFIX, False)

    @property
    def banned_heroes(self):
        """
        Generator for banned heroes in this series.
        """
        for hero in HEROES_DICT:
            if self.__getattribute__(hero + self._COLUMN_POSTFIX):
                yield hero


match_series_table = Table(
    "match_series",
    _mapper_registry.metadata,
    Column("id", Uuid(as_uuid=False), primary_key=True, default=generate_uuid),
    Column("created_at", DateTime, default=func.now()),
    Column("name", Text),
    Column("edit_key", Uuid(as_uuid=False), default=generate_uuid),
    *(
        Column(hero_name + MatchSeries._COLUMN_POSTFIX, Boolean, default=False)
        for hero_name in sorted(HEROES_DICT)
    ),
)
"""SQLAlchemy table for MatchSeries class."""


_mapper_registry.map_imperatively(MatchSeries, match_series_table)


class MatchSeriesManager:
    """
    A class that should be used to interact with the database.

    :param session: SQLAlchemy Session.
    :param id: ID of the Match Series this object should manage.
    :param edit_key:
        An optional edit key. Will be compared with the actual edit_key.
    """

    def __init__(self, session: Session, id: str, edit_key: Optional[str] = None):
        self.session = session
        stmt = select(MatchSeries).where(MatchSeries.id == id)
        self.match_series: MatchSeries = self.session.scalars(stmt).one()
        """A MatchSeries instance for the ID."""
        if edit_key is not None:
            self.edit_permission = self.match_series.edit_key == edit_key
            """Whether edit permission is granted to this manager."""
        else:
            self.edit_permission = False

    def set_hero_bans(self, ban_heroes: Iterable[str], unban_heroes: Iterable[str]):
        """
        Ban heroes from `ban_heroes`, then unban heroes from `unban_heroes`.

        :raises RuntimeError: If this manager does not have permission to edit bans.
        """
        if not self.edit_permission:
            raise RuntimeError("Insufficient permissions to edit match series.")

        for hero in ban_heroes:
            self.match_series._ban(hero)
        for hero in unban_heroes:
            self.match_series._unban(hero)
        self.session.commit()

    @staticmethod
    def create_new(session: Session, name: str, pre_banned_heroes: Iterable[str]):
        """
        Create new MatchSeries.

        :param session: SQLAlchemy session.
        :param name: Name of the series.
        :param pre_banned_heroes: An iterable with pre-banned heroes.
        :return: A MatchSeries instance.
        """
        match_series = MatchSeries(
            name=name,
        )
        for hero in pre_banned_heroes:
            match_series._ban(hero)
        session.add(match_series)
        session.commit()
        return match_series
