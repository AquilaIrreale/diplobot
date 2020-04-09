
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


from utils import StrEnum
from enum import auto
from database import db

#from sqlite3 import IntegrityError


class GameState(StrEnum):
    CREATED = auto()
    MAIN = auto()
    RETREAT = auto()
    BUILD = auto()
    DEFAULT = CREATED


class GameDate:
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def __add__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return GameDate(self.timestamp + other)

    def __iadd__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        self.timestamp += other
        return self

    def __sub__(self, other):
        if not isinstance(other, int):
            return NotImplemented
        return GameDate(self.timestamp - other)

    def __isub(self, other):
        if not isinstance(other, int):
            return NotImplemented
        self.timestamp -= other
        return self

    def __int__(self):
        return self.timestamp

    def __str__(self):
        is_bc = self.timestamp < 0
        is_spring = self.timestamp % 2 == 0
        year = abs(self.timestamp // 2)
        return "{}, {} {}".format(
            "Spring" if is_spring else "Fall",
            year if is_bc else year+1,
            "BC" if is_bc else "AD")

    @classmethod
    def parse(cls, s):
        raise NotImplementedError


class Game:
    def __init__(self, game_id):
        c = db.cursor()
        c.execute(
            "SELECT count(*) FROM games WHERE id = ?", (game_id,))
        if c.fetchone() == (0,):
            raise ValueError(f"There's no game with id {game_id}")
        self.game_id = game_id

    @classmethod
    def create(cls, game_id, start_date):
        c = db.cursor()
        c.execute(
            "INSERT INTO games(id, start_date, game_date, state)"
            "VALUES (?, ?, ?, ?)", (
                game_id,
                int(start_date),
                int(start_date),
                GameState.DEFAULT.value))
        db.commit()
        return cls(game_id)

    def _get_state(self):
        c = db.cursor()
        c.execute(
            "SELECT state "
            "FROM games "
            "WHERE id = ?",
            (self.game_id,))
        (state_str,) = c.fetchone()
        return GameState(state_str)

    def _set_state(self, state):
        c = db.cursor()
        c.execute(
            "UPDATE games "
            "SET state = ? "
            "WHERE id = ?",
            (GameState(state).value,
            self.game_id))
        db.commit()

    state = property(_get_state, _set_state)

    def add_player(self, player_id):
        raise NotImplementedError


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
