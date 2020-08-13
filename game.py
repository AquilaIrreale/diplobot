
  ############################################################################
  # Diplobot - play Diplomacy through Telegram                               #
  # Copyright (C) 2018 Simone Cimarelli a.k.a. AquilaIrreale                 #
  #                                                                          #
  # This program is free software: you can redistribute it and/or modify     #
  # it under the terms of the GNU Affero General Public License as published #
  # by the Free Software Foundation, either version 3 of the License, or     #
  # (at your option) any later version.                                      #
  #                                                                          #
  # This program is distributed in the hope that it will be useful,          #
  # but WITHOUT ANY WARRANTY; without even the implied warranty of           #
  # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
  # GNU Affero General Public License for more details.                      #
  #                                                                          #
  # You should have received a copy of the GNU Affero General Public License #
  # along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
  ############################################################################


from enum import auto
from utils import StrEnum, auto_repr

from sqlalchemy import Column, Boolean, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.types import TypeDecorator

from database import ORMBase
from board import Nation, Unit, Terr, TerrCoast


class GameState(StrEnum):
    CREATED = auto()
    MAIN    = auto()
    RETREAT = auto()
    BUILD   = auto()
    DEFAULT = CREATED


@auto_repr
class GameDate:
    def __init__(self, datestamp):
        self.datestamp = int(datestamp)

    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return GameDate(self.datestamp + other)

    def __iadd__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        self.datestamp += other
        return self

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return GameDate(self.datestamp - other)

    def __isub(self, other):
        if not isinstance(other, int):
            return NotImplemented
        self.datestamp -= other
        return self

    def __int__(self):
        return self.datestamp

    def __str__(self):
        is_bc = self.datestamp < 0
        is_spring = self.datestamp % 2 == 0
        year = abs(self.datestamp // 2)
        return "{}, {} {}".format(
            "Spring" if is_spring else "Fall",
            year if is_bc else year+1,
            "BC" if is_bc else "AD")

    @classmethod
    def parse(cls, s):
        raise NotImplementedError


class DateColumn(TypeDecorator):
    impl = Integer

    def process_bind_param(self, value, dialect):
        return int(value)

    def process_result_value(self, value, dialect):
        return GameDate(value)


class UserStringColumn(TypeDecorator):
    impl = String

    @property
    def cls(self):
        raise NotImplementedError

    def process_bind_param(self, value, dialect):
        return str(value)

    def process_result_value(self, value, dialect):
        return self.cls(value)


class StringEnumColumn(TypeDecorator):
    impl = String

    @property
    def cls(self):
        raise NotImplementedError

    def process_bind_param(self, value, dialect):
        return value.name

    def process_result_value(self, value, dialect):
        return self.parse(value)


class StateColumn(StringEnumColumn):
    cls = GameState


class NationColumn(StringEnumColumn):
    cls = Nation


class UnitColumn(UserStringColumn):
    cls = Unit


class TerrColumn(UserStringColumn):
    cls = Terr


class TerrCoastColumn(UserStringColumn):
    cls = TerrCoast


def type_coercer(**attrs):
    @validates(*attrs)
    def _validator(self, attr, val):
        return attrs[attr](val)
    return _validator


@auto_repr
class User(ORMBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    cur_game_id = Column(Integer, ForeignKey("games.id"))

    players = relationship("Player", back_populates="user")
    cur_game = relationship("Game")

    validator = type_coercer(id=int, cur_game_id=int)

    def __init__(self, id):
        self.id = id


@auto_repr
class Player(ORMBase):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    nation = Column(NationColumn, nullable=False)
    ready = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("game_id", "nation"),
        UniqueConstraint("user_id", "game_id")
    )

    user = relationship("User", back_populates="players")
    game = relationship("Game", back_populates="players")
    units = relationship("Unit", back_populates="owner")
    centers = relationship("Center", back_populates="owner")

    validator = type_coercer(
            id=int,
            user_id=int,
            game_id=int,
            nation=Nation,
            ready=bool)

    @validates("state")
    def validate_state(self, key, s):
        return s # TODO

    def __init__(self, id, nation):
        self.id = id
        self.nation = nation
        self.ready = False


#class Player:
#    def __init__(self, player_id):
#        c = db.cursor()
#        c.execute(
#            "SELECT count(*) FROM players WHERE id = ?", (player_id,))
#        if c.fetchone() == (0,):
#            raise ValueError(f"There's no player with id {player_id}")
#        self.player_id = player_id
#
#    def __repr__(self):
#        return f"Player({self.player_id})"


@auto_repr
class Game(ORMBase):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    start_date = Column(DateColumn, nullable=False)
    game_date = Column(DateColumn, nullable=False)
    state = Column(StateColumn, nullable=False)

    players = relationship(
            "Player",
            back_populates="game",
            collection_class=attribute_mapped_collection("nation"))
    units = relationship("Unit", back_populates="game")
    centers = relationship("Center", back_populates="game")

    validator = type_coercer(
            id=int,
            start_date=GameDate,
            game_date=GameDate,
            state=GameState)

    def __init__(self, id, start_date, game_date=None, state=GameState.DEFAULT):
        self.id = id
        self.start_date = start_date
        self.game_date = game_date if game_date is not None else start_date
        self.state = state


#class Game:
#    def __init__(self, game_id):
#        c = db.cursor()
#        c.execute(
#            "SELECT count(*) FROM games WHERE id = ?", (game_id,))
#        if c.fetchone() == (0,):
#            raise ValueError(f"There's no game with id {game_id}")
#        self.game_id = game_id
#
#    def __repr__(self):
#        return f"Game({self.game_id})"
#
#    @classmethod
#    def create(cls, game_id, start_date):
#        c = db.cursor()
#        c.execute(
#            "INSERT INTO games(id, start_date, game_date, state) "
#            "VALUES (?, ?, ?, ?)", (
#                game_id,
#                int(start_date),
#                int(start_date),
#                GameState.DEFAULT.value))
#        db.commit()
#        return cls(game_id)
#
#    def _get_state(self):
#        c = db.cursor()
#        c.execute(
#            "SELECT state "
#            "FROM games "
#            "WHERE id = ?",
#            (self.game_id,))
#        (state_str,) = c.fetchone()
#        return GameState(state_str)
#
#    def _set_state(self, state):
#        if not isinstance(new_state, GameState):
#            raise TypeError("new_state must be a GameState")
#        self._execute_transition(state)
#        c = db.cursor()
#        c.execute(
#            "UPDATE games "
#            "SET state = ? "
#            "WHERE id = ?",
#            (GameState(state).value,
#            self.game_id))
#        db.commit()
#
#    state = property(_get_state, _set_state)
#
#    @property
#    def start_date(self):
#        c = db.cursor()
#        c.execute(
#            "SELECT start_date "
#            "FROM games "
#            "WHERE id = ?",
#            (self.game_id,))
#        (datestamp,) = c.fetchone()
#        return GameDate(datestamp)
#
#    @property
#    def date(self):
#        c = db.cursor()
#        c.execute(
#            "SELECT game_date "
#            "FROM games "
#            "WHERE id = ?",
#            (self.game_id,))
#        (datestamp,) = c.fetchone()
#        return GameDate(datestamp)
#
#    def advance_date(self):
#        c = db.cursor()
#        c.execute(
#            "UPDATE games "
#            "SET game_date = ? "
#            "WHERE id = ?",
#            (int(self.date + 1),
#            self.game_id))
#        db.commit()
#
#    def add_player(self, player_id, nation):
#        c = db.cursor()
#        c.execute(
#            "INSERT INTO players(id, game_id, nation, ready) "
#            "VALUES (?, ?, ?, ?)", (
#                player_id,
#                self.game_id,
#                Nation(nation).value,
#                False))
#        db.commit()
#
#    _state_transitions = {
#        (GameState.CREATED, GameState.MAIN):    None,
#        (GameState.MAIN,    GameState.RETREAT): None,
#        (GameState.RETREAT, GameState.MAIN):    None,
#        (GameState.RETREAT, GameState.BUILD):   None,
#        (GameState.BUILD,   GameState.MAIN):    None
#    }
#
#    def _execute_transition(self, new_state):
#        old_state = self._get_state()
#        try:
#            transition_function = (
#                self._state_transitions[(old_state, new_state)])
#        except KeyError as e:
#            raise ValueError(
#                f"Going from {old_state} to {new_state} "
#                f"is an invalid state transition") from e
#        if transition_function:
#            transition_function(self)


@auto_repr
class Unit(ORMBase):
    __tablename__ = "units"

    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    terr = Column(TerrCoastColumn, primary_key=True)
    type = Column(UnitColumn, nullable=False)
    owner_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    game = relationship("Game", back_populates="units")
    owner = relationship("Player", back_populates="units")

    validator = type_coercer(
            game_id=int,
            terr=TerrCoast,
            type=Unit,
            owner_id=int)

    def __init__(self, terr, type):
        self.terr = terr
        self.type = type


@auto_repr
class Center(ORMBase):
    __tablename__ = "centers"

    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    terr = Column(TerrColumn, primary_key=True)
    owner_id = Column(Integer, ForeignKey("players.id"))

    __table_args__ = (UniqueConstraint("game_id", "terr"),)

    game = relationship("Game", back_populates="centers")
    owner = relationship("Player", back_populates="centers")

    validator = type_coercer(
            game_id=int,
            terr=Terr,
            owner_id=int)

    def __init__(self, terr):
        self.terr = terr


#from operator import attrgetter
#
#from board import Board
#from orders import OrderBuilder
#
#
#class Player:
#    def __init__(self, player_id, board):
#        self.id = player_id
#        self._nation = None
#        self._orders = set()
#        self.builder = OrderBuilder(board, self._orders)
#        self.ready = False
#        self.deleting = False
#
#        self.retreats = {}
#        self.destroyed = set()
#        self.retreat_choices = []
#
#        self.units_choices = []
#        self.units_done = False
#        self.units_options = {}
#        self.units_disbanding = False
#        self.units_delta = 0
#
#    def set_nation(self, nation):
#        self._nation = nation
#        self.builder.nation = nation
#
#    def set_orders(self, orders):
#        self._orders = orders
#        self.builder.orders = orders
#
#    nation = property(attrgetter("_nation"), set_nation)
#    orders = property(attrgetter("_orders"), set_orders)
#
#    def reset(self):
#        self.orders.clear()
#        self.ready = False
#        self.deleting = False
#
#    def get_handle(self, bot, chat_id):
#        return "@" + bot.getChatMember(chat_id, self.id).user.username
#
#
#class Game:
#    def __init__(self, chat_id):
#        self.board = Board()
#        self.chat_id = chat_id
#        self.state = "NEW"
#        self.players = {}
#        self.assigning = None
#        self.assigning_message = None
#        self.year = 1900
#        self.autumn = False
#
#    def add_player(self, player_id, bot=None):
#        player = Player(player_id, self.board)
#        self.players[player_id] = player
#
#        return player
#
#    def is_full(self):
#        return len(self.players) >= 7
#
#    def advance(self):
#        if self.autumn:
#            self.year += 1
#
#        if self.year == 0:
#            self.year = 1
#
#        self.autumn = not self.autumn
#
#    def season(self):
#        return "Autumn" if self.autumn else "Spring"
#
#    def printable_year(self):
#        return "{} {}".format(abs(self.year), "AD" if self.year > 0 else "BC")
#
#    def date(self):
#        return self.season() + " " + self.printable_year()
#
#
#def find_game_by_player_id(games, player_id):
#    try:
#        return next(g for g in games if player_id in g.players)
#
#    except StopIteration:
#        raise KeyError("Player `{}' not found".format(player_id))
