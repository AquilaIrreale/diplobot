
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


from operator import attrgetter

from board import Board
from order import OrderBuilder


class Player:
    def __init__(self, player_id, board):
        self.id = player_id
        self._nation = None
        self._orders = set()
        self.builder = OrderBuilder(board, self._orders)
        self.ready = False
        self.deleting = False

        self.retreats = {}
        self.destroyed = set()
        self.retreat_choices = []

        self.units_choices = []
        self.units_done = False
        self.units_options = {}
        self.units_disbanding = False
        self.units_delta = 0

    def set_nation(self, nation):
        self._nation = nation
        self.builder.nation = nation

    def set_orders(self, orders):
        self._orders = orders
        self.builder.orders = orders

    nation = property(attrgetter("_nation"), set_nation)
    orders = property(attrgetter("_orders"), set_orders)

    def reset(self):
        self.orders.clear()
        self.ready = False
        self.deleting = False

    def get_handle(self, bot, chat_id):
        return "@" + bot.getChatMember(chat_id, self.id).user.username


class Game:
    def __init__(self, chat_id):
        self.board = Board()
        self.chat_id = chat_id
        self.state = "NEW"
        self.players = {}
        self.assigning = None
        self.assigning_message = None
        self.year = 1900
        self.autumn = False

    def add_player(self, player_id, bot=None):
        player = Player(player_id, self.board)
        self.players[player_id] = player

        return player

    def is_full(self):
        return len(self.players) >= 7

    def advance(self):
        if self.autumn:
            self.year += 1

        if self.year == 0:
            self.year = 1

        self.autumn = not self.autumn

    def season(self):
        return "Autumn" if self.autumn else "Spring"

    def printable_year(self):
        return "{} {}".format(abs(self.year), "AD" if self.year > 0 else "BC")

    def date(self):
        return self.season() + " " + self.printable_year()


def find_game_by_player_id(games, player_id):
    try:
        return next(g for g in games if player_id in g.players)

    except StopIteration:
        raise KeyError("Player `{}' not found".format(player_id))
