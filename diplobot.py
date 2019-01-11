#!/usr/bin/env python3

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


import os
import re
import time
import random
import pprint
import logging

from copy import copy
from operator import attrgetter, itemgetter
from functools import partial

from telegram import (InlineKeyboardButton as IKB,
                      InlineKeyboardMarkup as IKM,
                      ParseMode,
                      ReplyKeyboardMarkup as RKM,
                      ReplyKeyboardRemove as RKRemove,
                      ChatAction)

from telegram.ext import (Updater,
                          CommandHandler,
                          MessageHandler,
                          CallbackQueryHandler,
                          Filters)

from telegram.error import BadRequest, TimedOut

from utils import make_grid
from board import *
from order import *
from game import *
from adjudicator import adjudicate
from graphics import render_board

from guards import (group_chat,
                    private_chat,
                    game_in_chat,
                    no_game_in_chat,
                    player_in_this_game,
                    player_in_game,
                    game_state,
                    player_ready,
                    player_not_ready,
                    player_not_building_order,
                    player_not_deleting_orders)


class Diplobot:
    def __init__(self):
        self.games = {}

    def print_board(self, bot, game):
        bot.send_chat_action(game.chat_id, ChatAction.UPLOAD_PHOTO)

        board_png = render_board(game.board)

        with open(board_png, "b") as fd:
            bot.send_photo(
                game.chat_id, fd, "State of the board ({})".format(game.date()))

        os.unlink(board_png)

    def print_board_old(self, bot, game):
        message = "DEBUG: state of the board\n\n"

        for t in sorted(game.board.occupied() | supp_centers, key=str.casefold):
            info = []

            if game.board[t].occupied:
                info.append("Occ. " + game.board[t].occupied)

            if t in supp_centers:
                info.append("Own. " + str(game.board[t].owner))

            if not info:
                continue

            message += t + ": " + ", ".join(info) + "\n"

        bot.send_message(game.chat_id, message)

    def start_cmd(self, bot, update):
        update.message.reply_text("DiploBot started!", quote=False)

    def help_cmd(self, bot, update):
        update.message.reply_text("There's no help right now", quote=False)

    @group_chat
    @no_game_in_chat
    def newgame_cmd(self, bot, update):
        chat_id = update.message.chat.id
        from_id = update.message.from_user.id

        #TODO: vote?

        new_game = Game(chat_id)
        games[chat_id] = new_game

        bot.send_message(chat_id,
                         "A new <i>Diplomacy</i> game is starting!\n"
                         "Join now with /join",
                         parse_mode=ParseMode.HTML)

        player = new_game.add_player(from_id, bot)

        handle = player.get_handle(bot, chat_id)
        bot.send_message(chat_id, handle + " joined the game")

    @group_chat
    @game_in_chat
    @player_in_this_game
    def closegame_cmd(self, bot, update, game, player):
        # TODO: vote to close!

        if game.assigning:
            try:
                game.assigning_message.edit_reply_markup()
            except BadRequest:
                pass

        del games[game.chat_id]

        for p in game.players.values():
            bot.send_message(p.id, "Game closed", reply_markup=RKRemove())

        update.message.reply_text("Game closed", quote=False)

    @group_chat
    @game_in_chat
    def join_cmd(self, bot, update, game):
        user_id = update.message.from_user.id
        handle = "@" + update.message.from_user.username

        if game.state != "NEW":
            update.message.reply_text(
                handle + " you can't join right now", quote=False)

            return

        if user_id in game.players:
            update.message.reply_text(
                handle + " you already have joined this game", quote=False)

            return

        for g in games.values():
            if user_id in g.players:
                update.message.reply_text(
                    handle + " you are in another game already", quote=False)

                return

        player = game.add_player(user_id, bot)

        handle = player.get_handle(bot, game.chat_id)
        bot.send_message(game.chat_id, handle + " joined the game")

        if not game.is_full():
            return

        update.message.reply_text("All the players have joined", quote=False)
        startgame(bot, game)

    @group_chat
    @game_in_chat
    @player_in_this_game
    @game_state("NEW")
    def startgame_cmd(self, bot, update, game, player):
        #TODO: uncomment this!
        #if len(game.players) < 2:
        #    update.message.reply_text(
        #        "At least two people have to join before the game can start", quote=False)
        #
        #    return

        startgame(bot, game)

    def startgame(self, bot, game):
        game.state = "CHOOSING_NATIONS"

        bot.send_message(game.chat_id, "The game will begin shortly...")
        show_nations_menu(bot, game)

    def show_nations_menu(self, bot, game):
        players = game.players.values()

        try:
            player = random.choice(
                [p for p in players if p.nation is None])

        except IndexError:
            nations_menu_finalize(bot, game)
            return

        taken = {p.nation for p in players}
        available = [n for n in nations if n not in taken]
        available.append("RANDOM")

        keyboard = IKM([
            [IKB(n, callback_data="NATION_" + n)]
            for n in available
        ])

        handle = player.get_handle(bot, game.chat_id)
        message = bot.send_message(
            game.chat_id, handle + " choose a nation", reply_markup=keyboard)

        game.assigning = player.id
        game.assigning_message = message

    def nations_menu_cbh(self, bot, update):
        error = False

        try:
            game = games[update.callback_query.message.chat.id]
        except KeyError:
            error = True

        if error or game.state != "CHOOSING_NATIONS":
            update.callback_query.answer("This control is no longer valid")
            update.callback_query.message.edit_reply_markup()
            return

        player_id = update.callback_query.from_user.id

        if player_id != game.assigning:
            update.callback_query.answer(
                "Wait your turn" if player_id in game.players
                else "You can't use this control")
            return

        player = game.players[player_id]
        player.nation = update.callback_query.data[7:]

        handle = player.get_handle(bot, game.chat_id)

        for _ in range(10):
            try:
                update.callback_query.message.edit_reply_markup()
                update.callback_query.message.edit_text(
                    "{} will play as {}".format(handle, player.nation))
            except TimedOut as e:
                pass
            else:
                break

        else:
            raise e

        show_nations_menu(bot, game)

    def nations_menu_finalize(self, bot, game):
        game.assigning = None
        game.assigning_message = None

        taken = {p.nation for p in game.players.values()}
        available = [n for n in nations if n not in taken]

        random.shuffle(available)

        for p in game.players.values():
            if p.nation == "RANDOM":
                p.nation = available.pop()

        show_year_menu(bot, game)

    def show_year_menu(self, bot, game):
        bot.send_message(game.chat_id, "What year should the game begin in?")

        game.state = "CHOOSING_YEAR"

    year_re = re.compile(r"^(\d*)\s*(AD|BC|CE|BCE)?$", re.IGNORECASE)

    def year_msg_handler(self, bot, update, game):
        text = update.message.text.strip()
        match = year_re.match(text)

        if match:
            year = int(match.group(1))

        if not match or year == 0:
            update.message.reply_text("That's not a valid year", quote=True)
            return

        sign = match.group(2)
        if sign and sign.upper() in {"BC", "BCE"}:
            year = -year

        game.year = year

        show_timeout_menu(bot, game)

    def show_timeout_menu(self, bot, game):
        game.state = "CHOOSING_TIMEOUT"

        # TODO: implement this

        game_start(bot, game)

    def game_start(self, bot, game):
        start_message = "<b>Nations have been assigned as follows:</b>\n\n"
        for p in game.players.values():
            handle = p.get_handle(bot, game.chat_id)
            start_message += "    {} as {}\n".format(handle, p.nation)

        start_message += "\nThe year is {}\nLet the game begin!".format(game.printable_year())

        bot.send_message(game.chat_id, start_message, parse_mode=ParseMode.HTML)

        turn_start(bot, game)

    def turn_start(self, bot, game):
        print_board(bot, game)

        game.state = "ORDER_PHASE"

        bot.send_message(
            game.chat_id,
            "<b>Awaiting orders for {}</b>".format(game.date()),
            parse_mode=ParseMode.HTML)

        for p in game.players.values():
            p.reset()
            bot.send_message(
                p.id, "<b>Awaiting orders for {}</b>".format(game.date()),
                parse_mode=ParseMode.HTML)

            show_command_menu(bot, game, p)

    def show_command_menu(self, bot, game, player):
        message = ""
        for index, order in enumerate(sorted(player.orders), 1):
            message += "{}. {}\n".format(index, str(order)) # TODO: use long formatting

        if message:
            message += "\n"

        message += ("/new - submit a new order\n"
                    "/delete - withdraw an order\n"
                    "/ready - when you are done")

        bot.send_message(player.id, message, reply_markup=RKRemove())

    @private_chat
    @player_in_game
    @game_state("ORDER_PHASE")
    @player_not_ready
    @player_not_building_order
    @player_not_deleting_orders
    def new_cmd(self, bot, update, game, player):
        if not player.builder.unordered():
            update.message.reply_text("You have already sent orders to all of your units. "
                                      "/delete the orders you want to change, or send /ready "
                                      "when you are ready")
            return

        player.builder.new()

        show_order_menu(bot, game, player)

    order_menu_prompts = {
        "COAST": "North coast or south coast?",
        "KIND":  "Order kind?",
        "ORIG":  "From?",
        "TARG":  "To?",
        "VIAC":  "Put a \"via convoy\" specifier?"
    }

    def show_order_menu(self, bot, game, player, ntf=None):
        if not ntf:
            ntf = player.builder.next_to_fill()

        if ntf == "TERR":
            terrs = ", ".join(player.builder.terrs)

            if not terrs:
                prompt = "Who is this order for?"
            elif not player.builder.terr_remove:
                prompt = "{}\nAny others?".format(terrs)
            else:
                prompt = "{}\nWho do you want to remove?".format(terrs)
        else:
            prompt = order_menu_prompts[ntf]

        bot.send_message(
            player.id, prompt, reply_markup=player.builder.get_keyboard())

    def order_msg_handler(self, bot, update, game, player):
        try:
            ntf = player.builder.push(update.message.text)

        except ValueError:
            update.message.reply_text("Invalid input")

        except IndexError:
            player.builder.pop()
            show_command_menu(bot, game, player)

        except BuilderError as e:
            update.message.reply_text(e.message)

        else:
            if ntf == "DONE":
                player.orders.update(player.builder.pop())
                show_command_menu(bot, game, player)

            else:
                show_order_menu(bot, game, player, ntf)

    @private_chat
    @player_in_game
    @game_state("ORDER_PHASE")
    @player_not_ready
    @player_not_building_order
    @player_not_deleting_orders
    def delete_cmd(self, bot, update, game, player):
        update.message.reply_text("Which orders do you want to delete? (back to abort)")
        player.deleting = True

    parse_delete_num_re = re.compile(r"^(\d+)$")
    parse_delete_range_re = re.compile(r"^(\d+)\s*-\s*(\d+)$")

    def parse_delete_msg(self, s, n):
        ss = s.split(",")

        for s in map(str.strip, ss):
            match1 = parse_delete_num_re.match(s)
            match2 = parse_delete_range_re.match(s)

            if match1:
                a = int(match1.group(1))
                b = a

            elif match2:
                a = int(match2.group(1))
                b = int(match2.group(2))

            else:
                raise ValueError

            if a < 1 or b < a or b > n:
                raise ValueError

            yield range(a-1, b)

    def delete_msg_handler(self, bot, update, game, player):
        if update.message.text.strip().upper() == "BACK":
            player.deleting = False
            show_command_menu(bot, game, player)
            return

        try:
            ranges = set(parse_delete_msg(update.message.text, len(player.orders)))
        except ValueError:
            update.message.reply_text("Invalid input")
            return

        orders = sorted(player.orders)

        for r in ranges:
            for i in r:
                orders[i] = None

        player.orders = set(filter(None, orders))
        player.deleting = False

        show_command_menu(bot, game, player)

    @private_chat
    @player_in_game
    @game_state("ORDER_PHASE")
    @player_not_ready
    @player_not_building_order
    @player_not_deleting_orders
    def ready_cmd(self, bot, update, game, player):
        update.message.reply_text("Orders committed. Withdraw with /unready")
        player.ready = True
        ready_check(bot, game)

    @private_chat
    @player_in_game
    @game_state("ORDER_PHASE")
    @player_ready
    def unready_cmd(self, bot, update, game, player):
        update.message.reply_text("Orders withdrawn")
        player.ready = False
        show_command_menu(bot, game, player)

    def ready_check(self, bot, game):
        if all(p.ready for p in game.players.values()):
            if game.state == "ORDER_PHASE":
                run_adjudication(bot, game)

    def run_adjudication(self, bot, game):
        game.state = "ADJUDICATING"

        data = [
            (p.nation, p.get_handle(bot, game.chat_id), sorted(p.orders))
            for p in sorted(game.players.values(), key=attrgetter("nation"))
        ]

        orders = list(chain(*(os for n, h, os in data)))
        resolutions, retreats = adjudicate(game.board, orders)

        for p in game.players.values():
            dislodged = {t for t in retreats if game.board[t].occupied == p.nation}

            p.retreats = {t: retreats[t] for t in dislodged if retreats[t]}
            p.destroyed = {t for t in dislodged if not retreats[t]}

            p.retreat_choices = [
                (t, game.board[t].kind, None)
                for t in sorted(dislodged, key=str.casefold)
                if retreats[t]
            ]

            p.ready = False

        successful_moves = {
            (o.terr, o.targ)
            for o, r in zip(orders, resolutions)
            if r and o.kind == "MOVE"
        }

        apply_moves(game.board, successful_moves)

        res_it = iter(resolutions)
        message = "<b>ORDERS - {}</b>\n\n".format(game.date())

        no_orders = True

        for n, h, os in data:
            if not os:
                continue

            no_orders = False

            message += "{}: ({})\n".format(n, h)

            for o in os:
                res_mark = ("\N{OK HAND SIGN}"
                            if next(res_it)
                            else "\N{OPEN HANDS SIGN}")

                message += "{} {}\n".format(str(o), res_mark) #TODO: use long format

            message += "\n"

        if no_orders:
            message += "None\n\n"

        if retreats:
            message += ("<b>These units have been dislodged:</b>\n"
                        + ", ".join(sorted(retreats.keys(), key=str.casefold)) + "\n\n"
                        + "Awaiting retreat orders")

        bot.send_message(game.chat_id, message, parse_mode=ParseMode.HTML)

        game.state = "RETREAT_PHASE"

        for p in game.players.values():
            show_retreats_menu(bot, game, p)

    def apply_moves(self, board, moves):
        nations = []
        kinds = []

        for t1, t2 in moves:
            nations.append(board[t1].occupied)
            kinds.append(board[t1].kind)
            board[t1].occupied = None
            board[t1].kind = None

        for (t1, t2), n, k in zip(moves, nations, kinds):
            board[t2].occupied = n
            board[t2].kind = k

    def show_retreats_menu(self, bot, game, player):
        if not player.retreat_choices and not player.destroyed:
            player.ready = True
            retreats_ready_check(bot, game)
            return

        message = "<b>Some of you units have been dislodged</b>\n\n"

        for t in player.destroyed:
            message += "<b>{}</b> has nowere to go and will be disbanded\n".format(t)

        for t1, k, t2 in player.retreat_choices:
            message += "<b>{}</b> can retreat to {}\n".format(
                t1, ", ".join(player.retreats[t1]))

        bot.send_message(player.id, message, parse_mode=ParseMode.HTML)

        if not player.retreat_choices:
            player.ready = True
            retreats_ready_check(bot, game)
            return

        show_retreats_prompt(bot, game, player)

    def show_retreats_prompt(self, bot, game, player):
        try:
            t = next(t1 for t1, k, t2 in player.retreat_choices if t2 is None)
        except StopIteration:
            message = "The following retreats will be attempted:\n\n"

            for t1, k, t2 in player.retreat_choices:
                message += "{}-{}\n".format(t1, t2)

            message += "\nIs this correct"

            keyboard = [
                ["Yes", "No"],
            ]

            bot.send_message(player.id, message, reply_markup=RKM(keyboard))

            return

        keyboard = make_grid(sorted(player.retreats[t], key=str.casefold))

        keyboard.append(["Disband"])

        if next(t2 for t1, k, t2 in player.retreat_choices) is not None:
            keyboard.append(["Back"])

        bot.send_message(
            player.id, "Where should {} retreat to?".format(t),
            reply_markup=RKM(keyboard))

    def retreat_msg_handler(self, bot, update, game, player):
        s = update.message.text.strip().upper()

        try:
            t1, k, i = next(
                (t1, k, i)
                for i, (t1, k, t2)
                in enumerate(player.retreat_choices)
                if t2 is None)

        except StopIteration:
            if s in {"Y", "YES"}:
                player.ready = True
                update.message.reply_text(
                    "Retreats committed", reply_markup=RKRemove())
                retreats_ready_check(bot, game)

            elif s in {"N", "NO"}:
                t1, k, t2 = player.retreat_choices[-1]
                player.retreat_choices[-1] = (t1, k, None)
                show_retreats_prompt(bot, game, player)

            else:
                update.message.reply_text("Invalid input")

            return

        if s == "BACK":
            if i == 0:
                update.message.reply_text("Invalid input")

            else:
                player.retreat_choices[i-1] = (t1, k, None)
                show_retreats_prompt(bot, game, player)

            return

        if s == "DISBAND":
            player.retreat_choices[i] = (t1, k, False)
            show_retreats_prompt(bot, game, player)
            return

        try:
            t2 = terr_names.match_case(s)
        except KeyError:
            update.message.reply_text("Invalid input")
            return

        if t2 not in player.retreats[t1]:
            update.message.reply_text("Can't retreat in " + t2)
            return

        player.retreat_choices[i] = (t1, k, t2)
        show_retreats_prompt(bot, game, player)

    def retreats_ready_check(self, bot, game):
        if all(p.ready for p in game.players.values()):
            execute_retreats(bot, game)

    def execute_retreats(self, bot, game):
        retreats = set()
        destroyed = set()

        for p in game.players.values():
            retreats.update(p.retreat_choices)
            destroyed.update(p.destroyed)

        seen = set()
        dupes = set()

        for t1, k, t2 in retreats:
            if not t2:
                continue

            if t2 in seen:
                dupes.add(t2)
                continue

            seen.add(t2)

        for p in game.players.values():
            for t1, k, t2 in p.retreat_choices:
                if t2 and t2 not in dupes:
                    game.board[t2].occupied = p.nation
                    game.board[t2].kind = k

        bad_retreats = sorted(
            filter(lambda r: r[2] in dupes, retreats),
            key=lambda r: (r[2].casefold(), r[0].casefold()))

        good_retreats = sorted(
            filter(lambda r: r[2] not in dupes, retreats),
            key=lambda r: (r[0].casefold(), r[2].casefold()))

        message = ""

        if destroyed:
            message += ("These units couldn't retreat and have been disbanded\n\n"
                        + ", ".join(sorted(destroyed, key=str.casefold)) + "\n")

        if good_retreats:
            message += "\nThe following retreat orders have been carried out\n"

            for t1, k, t2 in good_retreats:
                if t2:
                    message += "{}-{}\n".format(t1, t2)
                else:
                    message += "{} disband\n".format(t1)

            message += "\n"

        if bad_retreats:
            message += ("\nThe following retreat orders were in conflict "
                        "and were not carried out. The corresponding units "
                        "have been disbanded\n")

            for t1, k, t2 in bad_retreats:
                message += "{}-{}\n".format(t1, t2)

        if message:
            bot.send_message(game.chat_id, message)

        if game.autumn:
            update_centers(bot, game)
        else:
            game.advance()
            turn_start(bot, game)

    def check_victory(self, bot, game):
        if len(game.players) == 1:
            winner = next(p for p in game.players.values())

        else:
            try:
                winner = next(p for p in game.players.values()
                              if len(game.board.owned(p.nation)) >= 18)

            except StopIteration:
                return False

        bot.send_message(
            winner.id, "<b>You won!</b>",
            parse_mode=ParseMode.HTML)

        bot.send_message(
            game.chat_id,
            "<b>{} ({}) wins!</b>".format(
                winner.nation, winner.get_handle(bot, game.chat_id)),
            parse_mode=ParseMode.HTML)

        del games[game.chat_id]

        return True

    def distance_from_home(self, t, nation):
        distances = full_graph.distances(t)
        return min(distances[hsc] for hsc in home_centers[nation])

    def auto_disband(self, board, nation, n):
        candidates = sorted(
            (
                distance_from_home(t, nation),
                0 if board[t].kind == "F" else 1,
                t.casefold(),
                t
            )

            for t in board.occupied(nation)
        )

        disbanding = map(itemgetter(3), candidates[:n])

        for t in disbanding:
            board[t].occupied = None
            board[t].kind = None
            board[t].coast = None

    def update_centers(self, bot, game):
        game.state = "BUILDING_PHASE"

        bot.send_message(game.chat_id, "Updating supply centers...")

        for t in supp_centers:
            if game.board[t].occupied:
                game.board[t].owner = game.board[t].occupied

        if check_victory(bot, game):
            return

        playing_nations = {p.nation: p for p in game.players.values()}

        for n in nations:
            try:
                p = playing_nations[n]
            except KeyError:
                p = None

            units = game.board.occupied(n)
            centers = game.board.owned(n)

            if p and not centers:
                for t in units:
                    game.board[t].occupied = None
                    game.board[t].kind = None
                    game.board[t].coast = None

                bot.send_message(p.id, "You lost!")
                bot.send_message(
                    game.chat_id, "{} ({}) was eliminated".format(
                        p.nation, p.get_handle(bot, game.chat_id)))

                game.players = {k: v for k, v in game.players.items() if v is not p}

                if check_victory(bot, game):
                    return

                continue

            units_n = len(units)
            centers_n = len(centers)

            if not p:
                if units_n > centers_n:
                    auto_disband(game.board, n, units_n - centers_n)

                continue

            if units_n > centers_n:
                p.units_disbanding = True
                p.units_options = units
                p.units_delta = units_n - centers_n

            elif units_n < centers_n:
                p.units_disbanding = False

                p.units_options = (home_centers[p.nation]
                                   & centers
                                   - game.board.occupied())

                p.units_delta = min(
                    centers_n - units_n, len(p.units_options))

            p.units_done = False
            p.units_choices = []
            p.ready = not p.units_delta

            if not p.ready:
                show_units_menu(bot, game, p)

        units_ready_check(bot, game)

    def show_units_menu(self, bot, game, player):
        if player.units_disbanding:
            bot.send_message(
                player.id,
                "Supply centers have been updated.\n"
                "You have to disband {} of your units".format(
                    player.units_delta))

            show_disband_prompt(bot, game, player)

        else:
            bot.send_message(
                player.id,
                "Supply centers have been updated.\n"
                "You can build up to {} new units".format(
                    player.units_delta))

            show_build_prompt(bot, game, player)

    def show_disband_prompt(self, bot, game, player):
        if not player.units_delta:
            message = ("These units will be disbanded: {}\n"
                       "Are you sure?".format(
                            ", ".join(player.units_choices)))

            keyboard = [["Yes", "No"]]

        else:
            keyboard = make_grid(sorted(
                player.units_options.difference(player.units_choices),
                key=str.casefold))

            if not player.units_choices:
                message = "Which unit should be disbanded{}?".format(
                    " first" if len(player.units_options) > 1 else "")

            else:
                message = "Disbanding {}. Who else?".format(
                    ", ".join(player.units_choices))

                keyboard.append(["Back"])

        bot.send_message(player.id, message, reply_markup=RKM(keyboard))

    def format_build(self, choices):
        s = ""

        for t, k, c in choices:
            s += "{} in {}{}\n".format(
                "An army" if k == "A" else "A fleet", t, c or "")

        return s

    def show_build_prompt(self, bot, game, player):
        try:
            t, k, c = player.units_choices[-1]
        except IndexError:
            t, k, c = True, True, True

        if not k:
            message = "What kind of unit do you want to build?"
            keyboard = [["Army", "Fleet"],
                        ["Back"]]

        elif not c and t in split_coasts and k == "F":
            message = "On which coast?"
            keyboard = [["North", "South"],
                        ["Back"]]

        elif not player.units_delta or player.units_done:
            if not player.units_choices:
                message = "No new units will be built."

            elif len(player.units_choices) == 1:
                message = ("This new unit will be built:\n\n"
                           + format_build(player.units_choices))

            else:
                message = ("These new units will be built:\n\n"
                           + format_build(player.units_choices))

            message += "\nAre you sure?"

            keyboard = [["Yes", "No"]]

        else:
            keyboard = make_grid(sorted(
                player.units_options - {t for t, k, c in player.units_choices},
                key=str.casefold))

            keyboard.append(["Done"])

            if not player.units_choices:
                message = "Where do you want to build?"

            else:
                message = ("Currently building:\n\n"
                           + format_build(player.units_choices)
                           + "\nWhat else?")

                keyboard.append(["Back"])

        bot.send_message(player.id, message, reply_markup=RKM(keyboard))

    def disband_msg_handler(self, bot, update, game, player):
        s = update.message.text.strip().upper()

        message = None

        if (player.units_choices
                and player.units_delta
                and s == "BACK"):

            player.units_choices.pop()
            player.units_delta += 1

        elif player.units_delta == 0:
            if s in {"Y", "YES"}:
                player.ready = True
                units_ready_check(bot, game)
                return

            elif s in {"N", "NO"}:
                player.units_choices.pop()
                player.units_delta += 1

            else:
                message = "Invalid input"

        else:
            try:
                t = terr_names.match_case(s)
            except KeyError:
                message = "Invalid input"
            else:
                available = player.units_options.difference(player.units_choices)

                if t not in available:
                    message = "Invalid input"
                else:
                    player.units_choices.append(t)
                    player.units_delta -= 1

        if message:
            bot.send_message(player.id, message)
            return

        show_disband_prompt(bot, game, player)

    def build_msg_handler(self, bot, update, game, player):
        s = update.message.text.strip().upper()

        if (player.units_choices
                and player.units_delta
                and not player.units_done
                and s == "BACK"):

            try:
                player.units_choices.pop()
            except IndexError:
                pass
            else:
                player.units_delta += 1

            show_build_prompt(bot, game, player)
            return

        message = None

        try:
            t, k, c = player.units_choices[-1]
        except IndexError:
            t, k, c = True, True, True

        if not k:
            if s in {"A", "ARMY"}:
                player.units_choices[-1] = t, "A", c
            elif s in {"F", "FLEET"}:
                player.units_choices[-1] = t, "F", c
            else:
                message = "Invalid input"

        elif not c and t in split_coasts and k == "F":
            if s in {"NORTH", "NORTH COAST", "NC", "(NC)"}:
                player.units_choices[-1] = t, k, "(NC)"
            elif s in {"SOUTH", "SOUTH COAST", "SC", "(SC)"}:
                player.units_choices[-1] = t, k, "(SC)"
            else:
                message = "Invalid input"

        elif player.units_done or player.units_delta == 0:
            if s in {"Y", "YES"}:
                player.ready = True
                units_ready_check(bot, game)
                return

            elif s in {"N", "NO"}:
                player.units_done = False

                if not player.units_delta and player.units_choices:
                    player.units_choices.pop()
                    player.units_delta += 1

            else:
                message = "Invalid input"

        elif s == "DONE":
            player.units_done = True

        else:
            try:
                t = terr_names.match_case(s)
            except KeyError:
                message = "Invalid input"
            else:
                available = (player.units_options
                             - {t for t, k, c in player.units_choices})

                if t not in available:
                    message = "Invalid input"
                else:
                    player.units_choices.append((t, infer_kind(t), None))
                    player.units_delta -= 1

        if message:
            bot.send_message(player.id, message)
            return

        show_build_prompt(bot, game, player)

    def units_ready_check(self, bot, game):
        if all(p.ready for p in game.players.values()):
            execute_builds_and_disbands(bot, game)

    def execute_builds_and_disbands(self, bot, game):
        for p in game.players.values():
            if p.units_disbanding:
                for t in p.units_choices:
                    game.board[t].occupied = None
                    game.board[t].kind = None
                    game.board[t].coast = None

            else:
                for t, k, c in p.units_choices:
                    game.board[t].occupied = p.nation
                    game.board[t].kind = k
                    game.board[t].coast = c

        game.advance()
        turn_start(bot, game)

    def general_group_msg_handler(self, bot, update):
        try:
            game = games[update.message.chat.id]
        except KeyError:
            return

        if game.state == "CHOOSING_YEAR":
            year_msg_handler(bot, update, game)

    def general_private_msg_handler(self, bot, update):
        player_id = update.message.chat.id

        try:
            game = find_game_by_player_id(self.games.values(), player_id)
        except KeyError:
            return

        player = game.players[player_id]

        if not player.ready:
            if game.state == "ORDER_PHASE":
                if player.builder:
                    order_msg_handler(bot, update, game, player)

                elif player.deleting:
                    delete_msg_handler(bot, update, game, player)

            elif game.state == "RETREAT_PHASE":
                retreat_msg_handler(bot, update, game, player)

            elif game.state == "BUILDING_PHASE":
                if player.units_disbanding:
                    disband_msg_handler(bot, update, game, player)

                else:
                    build_msg_handler(bot, update, game, player)

    def error_handler(self, bot, update, error):
        self.logger.warning("Got \"%s\" error while processing update:\n%s\n", error, pprint.pformat(update))

    cmd_re = re.compile("^(.*)_cmd$")
    cbh_re = re.compile("^(.*)_cbh$")

    def register_handlers(self, dispatcher):
        for member in dir(self):
            if not callable(member):
                continue

            m = cmd_re.match(member)
            if m:
                dispatcher.add_handler(
                    CommandHandler(
                        m.group(1),
                        partial(member, self)))

            m = cbh_re.match(member)
            if m:
                dispatcher.add_handler(
                    CallbackQueryHandler(
                        m.group(1),
                        partial(member, self)))

        dispatcher.add_handler(
            MessageHandler(
                Filters.text & Filters.group,
                partial(general_group_msg_handler, self)))

        dispatcher.add_handler(
            MessageHandler(
                Filters.text & Filters.private,
                partial(general_private_msg_handler, self)))

        dispatcher.add_error_handler(
            partial(error_handler, self))


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s %(message)s",
        level=logging.INFO)

    logger = logging.getLogger(__name__)

    try:
        f = open("token", "r")
    except OSError:
        logger.error("Token file not found")
        exit(1)

    with f:
        token = f.read().strip()

    updater = Updater(token, request_kwargs={
        'read_timeout': 15,
        'connect_timeout': 15
    })

    bot = Diplobot(logger)
    bot.register_handlers(updater.dispatcher)

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
