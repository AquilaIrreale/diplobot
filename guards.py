
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


def group_chat(f):
    def wrapper(self, bot, update):
        if update.message.chat.type == "group":
            f(self, bot, update)

        else:
            update.message.reply_text("This command can only be used in a group chat")

    return wrapper


def private_chat(f):
    def wrapper(self, bot, update):
        if update.message.chat.type == "private":
            f(self, bot, update)

        else:
            update.message.reply_text("This command can only be used in a private chat")

    return wrapper


def game_in_chat(f):
    def wrapper(self, bot, update):
        try:
            f(self, bot, update, self.games[update.message.chat.id])

        except KeyError:
            update.message.reply_text(
                "There is no game currently running in this chat\n"
                "Start one with /newgame!")

    return wrapper


def no_game_in_chat(f):
    def wrapper(self, bot, update):
        if update.message.chat.id not in self.games:
            f(self, bot, update)

        else:
            update.message.reply_text("A game is already running in this chat")

    return wrapper


def player_in_this_game(f):
    def wrapper(self, bot, update, game):
        try:
            f(self, bot, update, game,
              game.players[update.message.from_user.id])

        except KeyError:
            update.message.reply_text("You are not a player in this game")

    return wrapper


def player_in_game(f):
    def wrapper(self, bot, update):
        p_id = update.message.chat.id

        try:
            game = next(g for g in self.games.values() if p_id in g.players)

        except StopIteration:
            update.message.reply_text("You need to join a game to use this command")

        else:
            f(self, bot, update, game, game.players[p_id])

    return wrapper


def game_state(*states):
    def decorator(f):
        def wrapper(self, bot, update, game, player):
            if game.state in states:
                f(self, bot, update, game, player)

            else:
                update.message.reply_text("You can't use this command right now")

        return wrapper

    return decorator


def player_ready(f):
    def wrapper(self, bot, update, game, player):
        if player.ready:
            f(self, bot, update, game, player)

        else:
            update.message.reply_text(
                "You have not committed your orders yet")

    return wrapper


def player_not_ready(f):
    def wrapper(self, bot, update, game, player):
        if not player.ready:
            f(self, bot, update, game, player)

        else:
            update.message.reply_text(
                "You have already committed you orders. Withdraw with /unready")

    return wrapper


def player_not_building_order(f):
    def wrapper(self, bot, update, game, player):
        if not player.builder:
            f(self, bot, update, game, player)

        else:
            update.message.reply_text(
                "You have an order to complete first")

    return wrapper


def player_not_deleting_orders(f):
    def wrapper(self, bot, update, game, player):
        if not player.deleting:
            f(self, bot, update, game, player)

        else:
            update.message.reply_text(
                "You have to tell me what orders to delete first "
                "(type back to abort)")

    return wrapper
