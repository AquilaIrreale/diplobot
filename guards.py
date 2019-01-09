
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


class HandlerGuard(Exception):
    pass


def group_chat(update):
    if update.message.chat.type != "group":
        update.message.reply_text("This command can only be used in a group chat")
        raise HandlerGuard


def private_chat(update):
    if update.message.chat.type != "private":
        update.message.reply_text("This command can only be used in a private chat")
        raise HandlerGuard


def game_exists(update):
    if update.message.chat.id not in games:
        update.message.reply_text(
            "There is no game currently running in this chat\n"
            "Start one with /newgame!")

        raise HandlerGuard

def player_in_game(update):
    try:
        return game_by_player(update.message.chat.id)
    except KeyError:
        update.message.reply_text("You need to join a game to use this command")
        raise HandlerGuard


def game_status(update, game, status):
    if game.state != status:
        update.message.reply_text("You can't use this command right now")
        raise HandlerGuard


def player_not_ready(update, player):
    if player.ready:
        update.message.reply_text(
            "You have already committed you orders. Withdraw with /unready",
            quote=False)

        raise HandlerGuard


def player_ready(update, player):
    if not player.ready:
        update.message.reply_text(
            "You have not committed your orders yet",
            quote=False)

        raise HandlerGuard


def player_not_building_order(update, player):
    if player.builder:
        update.message.reply_text(
            "You have an order to complete first",
            quote=False)

        raise HandlerGuard


def player_not_deleting_orders(update, player):
    if player.deleting:
        update.message.reply_text(
            "You have to tell me what orders to delete first "
            "(type back to abort)",
            quote=False)

        raise HandlerGuard
