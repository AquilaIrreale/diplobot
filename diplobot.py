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
import io
import re
import time
import random
import pprint
import logging
import tempfile
import subprocess

from copy import copy, deepcopy
from operator import attrgetter, itemgetter
from itertools import chain

import xml.etree.ElementTree as ET

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

from insensitive_list import InsensitiveList
from graph import Graph


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

nations = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]


def load_graph(filename):

    graph_dict = {}

    with open(filename) as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            t1, t2s = tuple(line.split(":"))
            t1 = t1.strip()

            graph_dict[t1] = set(s.strip() for s in t2s.split(" ") if s)

    return Graph(graph_dict)


sea_graph = load_graph("seagraph")
land_graph = load_graph("landgraph")


def strip_coast(t):
    return t[:3]


full_graph = Graph()

for t1, t2 in chain(sea_graph.edges(), land_graph.edges()):
    full_graph.add_edge((strip_coast(t1), strip_coast(t2)))

territories = {
    strip_coast(t) for t in chain(land_graph.vertices(), sea_graph.vertices())
}

terr_names = InsensitiveList(sorted({strip_coast(t) for t in territories}, key=str.upper))

offshore = {
    "AEG", "ADR", "BAL", "BAR", "BLA",
    "BOT", "EAS", "ENG", "HEL", "ION",
    "IRI", "LYO", "MAO", "NAO", "NTH",
    "NWG", "SKA", "TYS", "WES"
}

coast = set(map(strip_coast, sea_graph.vertices() - offshore))

bla_coast = {strip_coast(t) for t in sea_graph.neighbors({"BLA"})}
bal_coast = {strip_coast(t) for t in sea_graph.neighbors({"BAL", "BOT"})}
main_coast = {
    strip_coast(t)
    for t in sea_graph.neighbors(offshore - {"BLA", "BAL", "BOT"})
}

coasts = (bla_coast, bal_coast, main_coast)

split_coasts = {"Bul", "Spa", "StP"}

supp_centers = {
    "Ank", "Bel", "Ber", "Bre", "Bud",
    "Bul", "Con", "Den", "Edi", "Gre",
    "Hol", "Kie", "Lon", "Lvp", "Mar",
    "Mos", "Mun", "Nap", "Nwy", "Par",
    "Por", "Rom", "Rum", "Ser", "Sev",
    "Smy", "Spa", "StP", "Swe", "Tri",
    "Tun", "Ven", "Vie", "War"
}

home_centers = {
    "AUSTRIA" : {"Bud", "Tri", "Vie"},
    "ENGLAND" : {"Edi", "Lon", "Lvp"},
    "FRANCE"  : {"Bre", "Mar", "Par"},
    "GERMANY" : {"Ber", "Kie", "Mun"},
    "ITALY"   : {"Nap", "Rom", "Ven"},
    "RUSSIA"  : {"Mos", "Sev", "StP", "War"},
    "TURKEY"  : {"Ank", "Con", "Smy"}
}

def infer_kind(t):
    return ("F" if t in offshore else
            "A" if t not in coast else None)


class Territory:
    def __init__(self, owner=None, occupied=None, kind=None, coast=None):
        self.owner = owner
        self.occupied = occupied
        self.kind = kind
        self.coast = coast


def make_board():
    return {
        "Alb": Territory(),
        "Ank": Territory(owner="TURKEY",  occupied="TURKEY",  kind="F"),
        "Apu": Territory(),
        "Arm": Territory(),
        "Bel": Territory(),
        "Ber": Territory(owner="GERMANY", occupied="GERMANY", kind="A"),
        "Boh": Territory(),
        "Bre": Territory(owner="FRANCE",  occupied="FRANCE",  kind="F"),
        "Bud": Territory(owner="AUSTRIA", occupied="AUSTRIA", kind="A"),
        "Bul": Territory(),
        "Bur": Territory(),
        "Cly": Territory(),
        "Con": Territory(owner="TURKEY",  occupied="TURKEY",  kind="A"),
        "Den": Territory(),
        "Edi": Territory(owner="ENGLAND", occupied="ENGLAND", kind="F"),
        "Fin": Territory(),
        "Gal": Territory(),
        "Gas": Territory(),
        "Gre": Territory(),
        "Hol": Territory(),
        "Kie": Territory(owner="GERMANY", occupied="GERMANY", kind="F"),
        "Lon": Territory(owner="ENGLAND", occupied="ENGLAND", kind="F"),
        "Lvn": Territory(),
        "Lvp": Territory(owner="ENGLAND", occupied="ENGLAND", kind="A"),
        "Mar": Territory(owner="FRANCE",  occupied="FRANCE",  kind="A"),
        "Mos": Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="A"),
        "Mun": Territory(owner="GERMANY", occupied="GERMANY", kind="A"),
        "NAf": Territory(),
        "Nap": Territory(owner="ITALY",   occupied="ITALY",   kind="F"),
        "Nwy": Territory(),
        "Par": Territory(owner="FRANCE",  occupied="FRANCE",  kind="A"),
        "Pic": Territory(),
        "Pie": Territory(),
        "Por": Territory(),
        "Pru": Territory(),
        "Rom": Territory(owner="ITALY",   occupied="ITALY",   kind="A"),
        "Ruh": Territory(),
        "Rum": Territory(),
        "Ser": Territory(),
        "Sev": Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="F"),
        "Sil": Territory(),
        "Smy": Territory(owner="TURKEY",  occupied="TURKEY",  kind="A"),
        "Spa": Territory(),
        "StP": Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="F",  coast="(SC)"),
        "Swe": Territory(),
        "Syr": Territory(),
        "Tri": Territory(owner="AUSTRIA", occupied="AUSTRIA", kind="F"),
        "Tun": Territory(),
        "Tus": Territory(),
        "Tyr": Territory(),
        "Ukr": Territory(),
        "Ven": Territory(owner="ITALY",   occupied="ITALY",   kind="A"),
        "Vie": Territory(owner="AUSTRIA", occupied="AUSTRIA", kind="A"),
        "Wal": Territory(),
        "War": Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="A"),
        "Yor": Territory(),
        "AEG": Territory(),
        "ADR": Territory(),
        "BAL": Territory(),
        "BAR": Territory(),
        "BLA": Territory(),
        "BOT": Territory(),
        "EAS": Territory(),
        "ENG": Territory(),
        "HEL": Territory(),
        "ION": Territory(),
        "IRI": Territory(),
        "LYO": Territory(),
        "MAO": Territory(),
        "NAO": Territory(),
        "NTH": Territory(),
        "NWG": Territory(),
        "SKA": Territory(),
        "TYS": Territory(),
        "WES": Territory()
    }


def occupied(board, nation=None):
    if nation:
        return {t for t in territories if board[t].occupied == nation}
    else:
        return {t for t in territories if board[t].occupied}


def owned(board, nation=None):
    if nation:
        return {t for t in supp_centers if board[t].owner == nation}
    else:
        return {t for t in supp_centers if board[t].owner}


def set_style(e, key, value):
    style = e.get("style", default="")

    if re.match(r"\b{}:".format(key), style):
        style = re.sub(r"\b{}:[^;]*".format(key), "{}:{}".format(key, value), style)

    else:
        if style:
            style += ';'

        style += "{}:{}".format(key, value)

    e.set("style", style)


def del_style(e, key):
    style = e.get("style", default="")
    style = re.sub(r"\b{}:[^;]*;?".format(key), "", style)
    e.set("style", style)


board_svg = ET.parse("board.svg")

piece_re = re.compile(r"^\w{3}_[AF](_(NC|SC))?$")

for e in board_svg.getroot().iter():
    if piece_re.match(e.get("id", default="")):
        set_style(e, "display", "none")


nation_colors = {
    "AUSTRIA" : "#FE3A3A",
    "ENGLAND" : "#163BC7",
    "FRANCE"  : "#00E9FF",
    "GERMANY" : "#878787",
    "ITALY"   : "#00FF00",
    "RUSSIA"  : "#BE68D6",
    "TURKEY"  : "#F5F500"
}


def print_board(bot, game):
    bot.send_chat_action(game.chat_id, ChatAction.UPLOAD_PHOTO)

    board_copy = deepcopy(board_svg)
    root = board_copy.getroot()

    for t in owned(game.board) & supp_centers:
        e = root.find('.//*[@id="{}_dot"]'.format(t))
        color = nation_colors[game.board[t].owner]
        set_style(e, "fill", color)

    for t in occupied(game.board):
        k = game.board[t].kind
        c = game.board[t].coast

        piece_id = "{}_{}".format(t, k)

        if t in split_coasts and k == "F":
            piece_id += "_NC" if c == "(NC)" else "_SC"

        e = root.find('.//*[@id="{}"]/*'.format(piece_id))
        color = nation_colors[game.board[t].occupied]
        set_style(e, "fill", color)

        e = root.find('.//*[@id="{}"]'.format(piece_id))
        del_style(e, "display")

    svg_fd, svg_fn = tempfile.mkstemp()
    svg = os.fdopen(svg_fd, "wb")
    board_copy.write(svg)
    svg.close()

    png_fd, png_fn = tempfile.mkstemp()
    os.close(png_fd)

    subprocess.run(
        [
            "inkscape",
            "--export-png=" + png_fn,
            "--export-width=1280",
            "--export-height=1175",
            svg_fn
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

    png = open(png_fn, "rb")

    bot.send_photo(
        game.chat_id, png, "State of the board ({})".format(game.date()))

    os.unlink(png_fn)
    os.unlink(svg_fn)


def print_board_old(bot, game):
    message = "DEBUG: state of the board\n\n"

    for t in sorted(occupied(game.board) | supp_centers, key=str.upper):
        info = []

        if game.board[t].occupied:
            info.append("Occ. " + game.board[t].occupied)

        if t in supp_centers:
            info.append("Own. " + str(game.board[t].owner))

        if not info:
            continue

        message += t + ": " + ", ".join(info) + "\n"

    send_with_retry(bot, game.chat_id, message)


def reachables(t, board):
    if not board[t].occupied:
        return set()

    if board[t].kind == "F":
        g = sea_graph

        if t in split_coasts:
            t += board[t].coast

    else:
        g = land_graph

    return {strip_coast(x) for x in g.neighbors({t})}


def reachables_via_c(t, board, excluded={}):
    if t not in coast or not board[t].occupied or board[t].kind != "A":
        return set()

    checked = set()
    to_check = full_graph.neighbors({t}) & offshore
    ret = set()

    while to_check:
        t1 = next(iter(to_check))
        to_check.discard(t1)
        checked.add(t1)

        if not board[t1].occupied or t1 in excluded:
            continue

        for t2 in sea_graph.neighbors({t1}):
            t2 = strip_coast(t2)

            if t2 in coast:
                ret.add(t2)

            elif t2 not in checked:
                to_check.add(t2)

    ret.discard(t)

    return ret


def contiguous_fleets(ts, board):
    nations = {board[t].occupied for t in ts if board[t].occupied}
    to_check = sea_graph.neighbors(ts)
    ret = copy(ts)

    while to_check:
        t = to_check.pop()

        if (t in offshore
                and board[t].occupied
                and board[t].occupied not in nations):

            ret.add(t)

            to_check |= sea_graph.neighbors({t}) - ret

    return ret


class Order:
    def __init__(self):
        self.kind = None
        self.terr = None
        self.orig = None
        self.targ = None
        self.coast = None
        self.via_c = None

    def __str__(self):
        coast = "{}".format(self.coast) if self.coast else ""
        via_c = " C" if self.via_c else ""

        if self.kind == "HOLD":
            return "{} H".format(self.terr)

        if self.kind == "MOVE":
            return "{}-{}{}{}".format(self.terr, self.targ, coast, via_c)

        if self.kind == "SUPH":
            return "{} S {}".format(self.terr, self.targ)

        if self.kind == "SUPM":
            return "{} S {}-{}".format(self.terr, self.orig, self.targ)

        if self.kind == "CONV":
            return "{} C {}-{}".format(self.terr, self.orig, self.targ)

        return "Invalid order"

    def key(self):
        if self.kind == "HOLD":
            ret = (0, self.terr,)
        elif self.kind == "SUPH":
            ret = (0, self.targ, self.terr)
        elif self.kind == "MOVE":
            ret = (1, self.terr, self.targ)
        elif self.kind == "SUPM":
            ret = (1, self.orig, self.targ, 0, self.terr)
        elif self.kind == "CONV":
            ret = (1, self.orig, self.targ, 1, self.terr)
        else:
            raise ValueError

        return tuple(x.lower() if isinstance(x, str) else x for x in ret)

    def __lt__(self, other):
        return self.key() < other.key()


class BuilderError(Exception):
    def __init__(self, message):
        super().__init__(self)
        self.message = message


class OrderBuilder:
    def __init__(self, board, orders, nation=None):
        self.board = board
        self.orders = orders
        self.nation = nation
        self.building = None
        self.terrs = set()
        self.terr_complete = False
        self.terr_remove = False
        self.more = False

    def __bool__(self):
        return self.building is not None

    def new(self):
        self.building = Order()
        self.terrs = set()
        self.terr_complete = False
        self.terr_remove = False
        self.more = False

    def pop(self):
        ret = set()
        for t in self.terrs:
            o = copy(self.building)
            o.terr = t
            ret.add(o)

        self.building = None
        return ret

    @property
    def terr(self):
        try:
            return next(iter(self.terrs))
        except StopIteration:
            return None

    def needs_via_c(self):
        t1 = self.terr
        t2 = self.building.targ

        if self.board[t1].kind == "F":
            return False

        if t2 not in land_graph.neighbors((t1,)):
            return False

        for c in coasts:
            if t1 in c and t2 in c:
                return True

        return False

    def auto_coast(self):
        if (self.board[self.terr].kind != "F"
                or self.building.targ not in split_coasts):

            return True

        i = 0

        for c in ("(NC)", "(SC)"):
            try:
                if self.terr in sea_graph.neighbors((self.building.targ + c,)):
                    self.building.coast = c
                    i += 1

            except KeyError:
                pass

        if i != 1:
            self.building.coast = None
            return False

        return True

    def next_to_fill(self):
        if self.building.kind is None:
            return "KIND"

        if not self.terr_complete:
            return "TERR"

        if self.building.kind == "HOLD":
            return "DONE"

        if self.building.orig is None and self.building.kind in {"SUPM", "CONV"}:
            return "ORIG"

        if self.building.targ is None:
            return "TARG"

        if self.building.kind == "MOVE":
            if self.building.via_c is None and self.needs_via_c():
                return "VIAC"
            elif self.building.coast is None and not self.auto_coast():
                return "COAST"

        return "DONE"

    kinds = {
        "H":               "HOLD",
        "HOL":             "HOLD",
        "HOLD":            "HOLD",
        "M":               "MOVE",
        "MOV":             "MOVE",
        "MOVE":            "MOVE",
        "ATTACK":          "MOVE",
        "MOVE (ATTACK)":   "MOVE",
        "SH":              "SUPH",
        "SUPPORT HOLD":    "SUPH",
        "SUPPORT TO HOLD": "SUPH",
        "SUPPORT A HOLD":  "SUPH",
        "SM":              "SUPM",
        "SUPPORT MOVE":    "SUPM",
        "SUPPORT TO MOVE": "SUPM",
        "SUPPORT A MOVE":  "SUPM",
        "C":               "CONV",
        "CON":             "CONV",
        "CONVOY":          "CONV"
    }

    kind_codes = set(kinds.values())

    def register_kind(self, s):
        try:
            self.building.kind = self.kinds[s]
        except KeyError:
            pass
        else:
            return

        if s in self.kind_codes:
            self.building.kind = s
        else:
            raise ValueError

    def register_terr_list(self, s):
        if s == "DONE":
            if not self.terrs:
                raise BuilderError("You must specify at least one territory")

            self.terr_complete = True
            self.more = False
            return

        if s == "REMOVE":
            if not self.terrs:
                raise ValueError

            self.terr_remove = True
            return

        if s == "ADD":
            self.terr_remove = False
            self.more = False
            return

        try:
            t = terr_names.match_case(s)
        except KeyError:
            raise ValueError

        if self.terr_remove:
            try:
                self.terrs.remove(t)
            except KeyError:
                raise ValueError

            if not self.terrs:
                self.terr_remove = False
        else:
            self.validate_terr(t)

            self.terrs.add(t)

            if self.building.kind not in {"SUPH", "SUPM", "CONV"}:
                self.terr_complete = True

    def register_orig(self, s):
        try:
            t = terr_names.match_case(s)
        except KeyError:
            raise ValueError

        self.validate_orig(t)

        self.building.orig = t
        self.more = False

    def register_targ(self, s):
        try:
            t = terr_names.match_case(s)
        except KeyError:
            raise ValueError

        self.validate_targ(t)

        self.building.targ = t
        self.more = False

    def register_viac(self, s):
        if s in {"YES", "Y"}:
            self.building.via_c = True
        elif s in {"NO", "N"}:
            self.building.via_c = False
        else:
            raise ValueError

    def register_coast(self, s):
        if s in {"N", "NC", "(NC)", "NORTH", "NORTH COAST"}:
            self.building.coast = "(NC)"
        elif s in {"S", "SC", "(SC)", "SOUTH", "SOUTH COAST"}:
            self.building.coast = "(SC)"
        else:
            raise ValueError

    actions = {
        "KIND":  lambda self, s: self.register_kind(s),
        "TERR":  lambda self, s: self.register_terr_list(s),
        "ORIG":  lambda self, s: self.register_orig(s),
        "TARG":  lambda self, s: self.register_targ(s),
        "VIAC":  lambda self, s: self.register_viac(s),
        "COAST": lambda self, s: self.register_coast(s)
    }

    back_attrs = ["via_c", "coast", "targ", "orig", "terrs", "kind"]

    def back(self):
        for attr in self.back_attrs:
            if attr != "terrs":
                if getattr(self.building, attr) is not None:
                    setattr(self.building, attr, None)
                    break

            elif self.terr_complete:
                break

        else:
            raise IndexError

        if attr in ["terrs", "kind"]:
            self.terrs = set()
            self.terr_complete = False

        self.more = False
        self.terr_remove = False

    def push(self, s):
        s = s.strip().upper()

        ntf = self.next_to_fill()

        if s == "BACK":
            self.back()

        elif s in {"MORE", "MORE..."}:
            self.more = not self.more

        elif ntf == "DONE":
            raise IndexError

        else:
            self.actions[ntf](self, s)

        return self.next_to_fill()

    def validate_terr(self, t):
        if not self.board[t].occupied:
            raise BuilderError("There's no unit in " + t)

        if self.board[t].occupied != self.nation:
            raise BuilderError("You can't order someone else's unit")

        if self.building.kind == "CONV":
            if self.board[t].kind != "F":
                raise BuilderError("Only fleets can convoy")

            elif t not in offshore:
                raise BuilderError("A fleet needs to be in open sea to convoy")


        for o in self.orders:
            if o.terr == t:
                raise BuilderError("There's already another order for {} ({})".format(t, o))

    def validate_orig(self, t):
        if t in self.terrs:
            raise BuilderError("{} is already part of the order".format(t))

    def validate_targ(self, t):
        t2 = self.terr if self.building.kind == "MOVE" else self.building.orig

        if t == t2:
            raise BuilderError("Can't move onto itself")

    def ordered(self):
        return {o.terr for o in self.orders}

    def unordered(self):
        return occupied(self.board, self.nation) - self.ordered()

    def get_terrs_hint(self):
        if self.terr_remove:
            return self.terrs

        available = self.unordered() - self.terrs

        if self.building.kind == "CONV":
            return available & offshore
        else:
            return available

    def get_origs_hint(self):
        ret = set()

        if self.building.kind == "SUPM":
            common_neighbors = copy(territories)

            for t in self.terrs:
                common_neighbors &= reachables(t, self.board)

            for t in territories:
                if (not reachables(t, self.board).isdisjoint(common_neighbors)
                        or not reachables_via_c(t, self.board, self.terrs)
                            .isdisjoint(common_neighbors)):

                    ret.add(t)

            ret -= self.terrs

        elif self.building.kind == "CONV":
            for t in sea_graph.neighbors(contiguous_fleets(self.terrs, self.board)):
                if self.board[t].occupied and self.board[t].kind == "A":
                    ret.add(t)

        return ret

    def get_targs_hint(self):
        if self.building.kind == "MOVE":
            return (reachables(self.terr, self.board)
                    | reachables_via_c(self.building.orig, self.board))

        if self.building.kind == "SUPH":
            return reachables(self.terr, self.board)

        elif self.building.kind == "SUPM":
            common_neighbors = copy(territories)

            for t in self.terrs:
                common_neighbors &= reachables(t, self.board)

            return (
                common_neighbors & (
                    reachables(self.building.orig, self.board)
                    | reachables_via_c(
                        self.building.orig, self.board, self.terrs)))

        elif self.building.kind == "CONV":
            return reachables_via_c(self.building.orig, self.board)


    hints = {
        "TERR": lambda self: self.get_terrs_hint(),
        "ORIG": lambda self: self.get_origs_hint(),
        "TARG": lambda self: self.get_targs_hint()
    }

    @staticmethod
    def get_kind_keyboard():
        return RKM([
            ["Hold"],
            ["Move (attack)"],
            ["Support to Hold"],
            ["Support to Move"],
            ["Convoy"],
            ["Back"]
        ])

    @staticmethod
    def get_coasts_keyboard():
        return RKM([
            ["North", "South"],
            ["Back"]
        ])

    @staticmethod
    def get_yesno_keyboard():
        return RKM([
            ["Yes", "No"],
            ["Back"]
        ])

    basic_keyboards = {
        "KIND":  lambda self: self.get_kind_keyboard(),
        "COAST": lambda self: self.get_coasts_keyboard(),
        "VIAC":  lambda self: self.get_yesno_keyboard()
    }

    def get_keyboard(self):
        ntf = self.next_to_fill()

        try:
            return self.basic_keyboards[ntf](self)
        except KeyError:
            pass

        try:
            hint = self.hints[ntf](self)
        except KeyError:
            return None

        if self.more:
            hint = territories - hint

        keyboard = make_grid(sorted(hint, key=str.upper))

        keyboard.append(["More..."])

        if ntf == "TERR" and self.terrs:
            if not self.terr_remove:
                keyboard.append(["Remove"])
            else:
                keyboard.append(["Add"])

            keyboard.append(["Done"])

        keyboard.append(["Back"])

        return RKM(keyboard)


def make_grid(l):
    r3 = len(l) % 3
    r4 = len(l) % 4

    if r4 == 0:
        cols = 4
    elif r3 == 0:
        cols = 3
    else:
        cols = 3 if r3 > r4 else 4

    return [l[i:i+cols] for i in range(0, len(l), cols)]


def format_board(board):
    ret = "CLEAR ALL\n"

    for name, t in board.items():
        if t.occupied:
            coast = t.coast or ""
            ret += "{}{} {} {}\n".format(name, coast, t.kind, t.occupied)

    return ret


def format_orders(orders):
    ret = ""

    for o in orders:
        if o.kind != "HOLD":
            ret += str(o) + "\n"

    return ret


res_re = re.compile(r"^\d+: (SUCCEEDS|FAILS)$")

def parse_res(s):
    m = res_re.match(s)

    if not m:
        raise ValueError(s)

    return m.group(1) == "SUCCEEDS"


ret_re = re.compile(r"^(\w+):(( \w+)*)$")

def parse_ret(s):
    m = ret_re.match(s)

    if not m:
        raise ValueError(s)

    t1 = terr_names.match_case(m.group(1))

    g2 = m.group(2) or ""

    t2s = {terr_names.match_case(t) for t in g2.split()}

    return t1, t2s


def adjudicate(board, orders):
    payload = format_board(board) + "\n" + format_orders(orders) + "\n"

    cp = subprocess.run(
        ["cdippy"], input=payload, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, universal_newlines=True)

    if cp.stderr:
        raise ValueError(payload)

    lines = iter(cp.stdout.splitlines())

    resolutions = [None if o.kind == "HOLD" else parse_res(next(lines)) for o in orders]

    if next(lines):
        raise ValueError(payload)

    retreats = {t1: t2s for t1, t2s in (parse_ret(s) for s in lines if s)}

    for i, o in enumerate(orders):
        if o.kind == "HOLD":
            resolutions[i] = o.terr not in retreats

    return resolutions, retreats


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
        self.board = make_board()
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

        if bot:
            handle = player.get_handle(bot, self.chat_id)
            send_with_retry(bot, self.chat_id, handle + " joined the game")

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

games = {}

def game_by_player(player_id):
    try:
        game = next(g for g in games.values() if player_id in g.players)
    except StopIteration:
        raise KeyError

    return game


## Guards
#########


class HandlerGuard(Exception):
    pass


def group_chat_guard(update):
    if update.message.chat.type != "group":
        reply_text_with_retry(update, "This command can only be used in a group chat")
        raise HandlerGuard


def private_chat_guard(update):
    if update.message.chat.type != "private":
        reply_text_with_retry(update, "This command can only be used in a private chat")
        raise HandlerGuard


def game_exists_guard(update):
    if update.message.chat.id not in games:
        reply_text_with_retry(
            update,
            "There is no game currently running in this chat\n"
            "Start one with /newgame!")

        raise HandlerGuard

def player_in_game_guard(update):
    try:
        return game_by_player(update.message.chat.id)
    except KeyError:
        reply_text_with_retry(update, "You need to join a game to use this command")
        raise HandlerGuard


def game_status_guard(update, game, status):
    if game.state != status:
        reply_text_with_retry(update, "You can't use this command right now")
        raise HandlerGuard


def player_not_ready_guard(update, player):
    if player.ready:
        reply_text_with_retry(
            update,
            "You have already committed you orders. Withdraw with /unready",
            quote=False)

        raise HandlerGuard


def player_ready_guard(update, player):
    if not player.ready:
        reply_text_with_retry(
            update,
            "You have not committed your orders yet",
            quote=False)

        raise HandlerGuard


def player_not_building_order_guard(update, player):
    if player.builder:
        reply_text_with_retry(
            update,
            "You have an order to complete first",
            quote=False)

        raise HandlerGuard


def player_not_deleting_orders_guard(update, player):
    if player.deleting:
        reply_text_with_retry(
            update,
            "You have to tell me what orders to delete first "
            "(type back to abort)",
            quote=False)

        raise HandlerGuard


## Handlers
###########


def start_cmd(bot, update):
    reply_text_with_retry(update, "DiploBot started!", quote=False)


def help_cmd(bot, update):
    reply_text_with_retry(update, "There's no help right now", quote=False)


def newgame(bot, chat_id, from_id):
    new_game = Game(chat_id)
    games[chat_id] = new_game

    send_with_retry(bot, chat_id,
                     "A new <i>Diplomacy</i> game is starting!\n"
                     "Join now with /join",
                     parse_mode=ParseMode.HTML)

    new_game.add_player(from_id, bot)


def newgame_cmd(bot, update):
    try:
        group_chat_guard(update)
    except HandlerGuard:
        return

    chat_id = update.message.chat.id
    from_id = update.message.from_user.id

    if chat_id not in games:
        newgame(bot, chat_id, from_id)
        return

    reply_text_with_retry(update, "A game is already running in this chat", quote=False)

    #TODO: vote?

    #game = games[chat_id]
    #
    #if from_id == game.adj_id:
    #    newgame_yes = IKB("Yes", callback_data="NEWGAME_YES")
    #    newgame_no  = IKB("No", callback_data="NEWGAME_NO")

    #    newgame_yesno = IKM([[newgame_yes, newgame_no]])

    #    update.message.reply_text("Would you like to start over?",
    #                              reply_markup = newgame_yesno, quote=False)


#def newgame_cbh(bot, update):
#    global games
#
#    chat_id = update.callback_query.message.chat.id
#    from_id = update.callback_query.from_user.id
#
#    if chat_id not in games:
#        update.callback_query.answer("Something went wrong")
#        return
#
#    game = games[chat_id]
#
#    if from_id != game.adj_id:
#        update.callback_query.answer("Only the adjudicator can use this button", show_alert = True)
#        return
#
#    update.callback_query.answer()
#    update.callback_query.message.edit_reply_markup()
#
#    if update.callback_query.data == "NEWGAME_YES":
#        update.callback_query.message.reply_text("Game closed")
#        newgame(bot, chat_id, from_id)


def closegame_cmd(bot, update):
    try:
        group_chat_guard(update)
        game_exists_guard(update)
    except HandlerGuard:
        return

    # TODO: vote to close!

    game = games[update.message.chat.id]

    if game.assigning:
        try:
            game.assigning_message.edit_reply_markup()
        except BadRequest:
            pass

    del games[update.message.chat.id]

    for p in game.players.values():
        send_with_retry(bot, p.id, "Game closed", reply_markup=RKRemove())

    reply_text_with_retry(update, "Game closed", quote=False)


def join_cmd(bot, update):
    try:
        group_chat_guard(update)
        game_exists_guard(update)
    except HandlerGuard:
        return

    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    handle = "@" + update.message.from_user.username

    game = games[chat_id]

    if game.state != "NEW":
        reply_text_with_retry(
            update, handle + " you can't join right now", quote=False)

        return

    if user_id in game.players:
        reply_text_with_retry(
            update, handle + " you already have joined this game", quote=False)

        return

    for g in games.values():
        if user_id in g.players:
            reply_text_with_retry(
                update, handle + " you are in another game already", quote=False)

            return

    game.add_player(user_id, bot)

    if not game.is_full():
        return

    reply_text_with_retry(update, "All the players have joined", quote=False)
    startgame(bot, game)


def startgame_cmd(bot, update):
    try:
        game_exists_guard(update)
    except HandlerGuard:
        return

    game = games[update.message.chat.id]

    #TODO: uncomment this!
    #if len(game.players) < 2:
    #    update.message.reply_text(
    #        "At least two people have to join before the game can start", quote=False)
    #
    #    return

    startgame(bot, game)


def startgame(bot, game):
    game.state = "CHOOSING_NATIONS"

    send_with_retry(bot, game.chat_id, "The game will begin shortly...")
    show_nations_menu(bot, game)


def show_nations_menu(bot, game):
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
    message = send_with_retry(
        bot, game.chat_id, handle + " choose a nation", reply_markup=keyboard)

    game.assigning = player.id
    game.assigning_message = message


def nations_menu_cbh(bot, update):
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


def nations_menu_finalize(bot, game):
    game.assigning = None
    game.assigning_message = None

    taken = {p.nation for p in game.players.values()}
    available = [n for n in nations if n not in taken]

    random.shuffle(available)

    for p in game.players.values():
        if p.nation == "RANDOM":
            p.nation = available.pop()

    show_year_menu(bot, game)


def show_year_menu(bot, game):
    send_with_retry(bot, game.chat_id, "What year should the game begin in?")

    game.state = "CHOOSING_YEAR"


year_re = re.compile(r"^(\d*)\s*(AD|BC|CE|BCE)?$", re.IGNORECASE)

def year_msg_handler(bot, update, game):
    text = update.message.text.strip()
    match = year_re.match(text)

    if match:
        year = int(match.group(1))

    if not match or year == 0:
        reply_text_with_retry(update, "That's not a valid year", quote=True)
        return

    sign = match.group(2)
    if sign and sign.upper() in {"BC", "BCE"}:
        year = -year

    game.year = year

    show_timeout_menu(bot, game)


def show_timeout_menu(bot, game):
    game.state = "CHOOSING_TIMEOUT"

    # TODO: implement this

    game_start(bot, game)


def game_start(bot, game):
    start_message = "<b>Nations have been assigned as follows:</b>\n\n"
    for p in game.players.values():
        handle = p.get_handle(bot, game.chat_id)
        start_message += "    {} as {}\n".format(handle, p.nation)

    start_message += "\nThe year is {}\nLet the game begin!".format(game.printable_year())

    send_with_retry(bot, game.chat_id, start_message, parse_mode=ParseMode.HTML)

    turn_start(bot, game)


def turn_start(bot, game):
    print_board(bot, game)

    game.state = "ORDER_PHASE"

    send_with_retry(
        bot, game.chat_id,
        "<b>Awaiting orders for {}</b>".format(game.date()),
        parse_mode=ParseMode.HTML)

    for p in game.players.values():
        p.reset()
        send_with_retry(
            bot, p.id, "<b>Awaiting orders for {}</b>".format(game.date()),
            parse_mode=ParseMode.HTML)

        show_command_menu(bot, game, p)


def show_command_menu(bot, game, player):
    message = ""
    for index, order in enumerate(sorted(player.orders), 1):
        message += "{}. {}\n".format(index, str(order)) # TODO: use long formatting

    if message:
        message += "\n"

    message += ("/new - submit a new order\n"
                "/delete - withdraw an order\n"
                "/ready - when you are done")

    send_with_retry(bot, player.id, message, reply_markup=RKRemove())


def new_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "ORDER_PHASE")

        player = game.players[update.message.chat.id]
        player_not_ready_guard(update, player)
        player_not_building_order_guard(update, player)
        player_not_deleting_orders_guard(update, player)

    except HandlerGuard:
        return

    if not player.builder.unordered():
        reply_text_with_retry(update, "You have already sent orders to all of your units. "
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

def show_order_menu(bot, game, player, ntf=None):
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

    send_with_retry(
        bot, player.id, prompt, reply_markup=player.builder.get_keyboard())


def order_msg_handler(bot, update, game, player):
    try:
        ntf = player.builder.push(update.message.text)

    except ValueError:
        reply_text_with_retry(update, "Invalid input")

    except IndexError:
        player.builder.pop()
        show_command_menu(bot, game, player)

    except BuilderError as e:
        reply_text_with_retry(update, e.message)

    else:
        if ntf == "DONE":
            player.orders.update(player.builder.pop())
            show_command_menu(bot, game, player)

        else:
            show_order_menu(bot, game, player, ntf)


def delete_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "ORDER_PHASE")

        player = game.players[update.message.chat.id]
        player_not_ready_guard(update, player)
        player_not_building_order_guard(update, player)
        player_not_deleting_orders_guard(update, player)

    except HandlerGuard:
        return

    reply_text_with_retry(update, "Which orders do you want to delete? (back to abort)")

    player.deleting = True


parse_delete_num_re = re.compile(r"^(\d+)$")
parse_delete_range_re = re.compile(r"^(\d+)\s*-\s*(\d+)$")

def parse_delete_msg(s, n):
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


def delete_msg_handler(bot, update, game, player):
    if update.message.text.strip().upper() == "BACK":
        player.deleting = False
        show_command_menu(bot, game, player)
        return

    try:
        ranges = set(parse_delete_msg(update.message.text, len(player.orders)))
    except ValueError:
        reply_text_with_retry(update, "Invalid input")
        return

    orders = sorted(player.orders)

    for r in ranges:
        for i in r:
            orders[i] = None

    player.orders = set(filter(None, orders))
    player.deleting = False

    show_command_menu(bot, game, player)


def ready_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "ORDER_PHASE")

        player = game.players[update.message.chat.id]
        player_not_ready_guard(update, player)
        player_not_building_order_guard(update, player)
        player_not_deleting_orders_guard(update, player)

    except HandlerGuard:
        return

    reply_text_with_retry(update, "Orders committed. Withdraw with /unready")

    player.ready = True

    ready_check(bot, game)


def unready_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "ORDER_PHASE")

        player = game.players[update.message.chat.id]
        player_ready_guard(update, player)

    except HandlerGuard:
        return

    reply_text_with_retry(update, "Orders withdrawn")

    player.ready = False

    show_command_menu(bot, game, player)


def ready_check(bot, game):
    if all(p.ready for p in game.players.values()):
        if game.state == "ORDER_PHASE":
            run_adjudication(bot, game)


def run_adjudication(bot, game):
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
            for t in sorted(dislodged, key=str.lower)
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
                    + ", ".join(sorted(retreats.keys(), key=str.lower)) + "\n\n"
                    + "Awaiting retreat orders")

    send_with_retry(bot, game.chat_id, message, parse_mode=ParseMode.HTML)

    game.state = "RETREAT_PHASE"

    for p in game.players.values():
        show_retreats_menu(bot, game, p)


def apply_moves(board, moves):
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


def show_retreats_menu(bot, game, player):
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

    send_with_retry(bot, player.id, message, parse_mode=ParseMode.HTML)

    if not player.retreat_choices:
        player.ready = True
        retreats_ready_check(bot, game)
        return

    show_retreats_prompt(bot, game, player)


def show_retreats_prompt(bot, game, player):
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

        send_with_retry(bot, player.id, message, reply_markup=RKM(keyboard))

        return

    keyboard = make_grid(sorted(player.retreats[t], key=str.lower))

    keyboard.append(["Disband"])

    if next(t2 for t1, k, t2 in player.retreat_choices) is not None:
        keyboard.append(["Back"])

    send_with_retry(
        bot, player.id, "Where should {} retreat to?".format(t),
        reply_markup=RKM(keyboard))


def retreat_msg_handler(bot, update, game, player):
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
            reply_text_with_retry(
                update, "Retreats committed", reply_markup=RKRemove())
            retreats_ready_check(bot, game)

        elif s in {"N", "NO"}:
            t1, k, t2 = player.retreat_choices[-1]
            player.retreat_choices[-1] = (t1, k, None)
            show_retreats_prompt(bot, game, player)

        else:
            reply_text_with_retry(update, "Invalid input")

        return

    if s == "BACK":
        if i == 0:
            reply_text_with_retry(update, "Invalid input")

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
        reply_text_with_retry(update, "Invalid input")
        return

    if t2 not in player.retreats[t1]:
        reply_text_with_retry(update, "Can't retreat in " + t2)
        return

    player.retreat_choices[i] = (t1, k, t2)
    show_retreats_prompt(bot, game, player)


def retreats_ready_check(bot, game):
    if all(p.ready for p in game.players.values()):
        execute_retreats(bot, game)


def execute_retreats(bot, game):
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
        key=lambda r: (r[2].upper(), r[0].upper()))

    good_retreats = sorted(
        filter(lambda r: r[2] not in dupes, retreats),
        key=lambda r: (r[0].upper(), r[2].upper()))

    message = ""

    if destroyed:
        message += ("These units couldn't retreat and have been disbanded\n\n"
                    + ", ".join(sorted(destroyed, key=str.lower)) + "\n")

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
        send_with_retry(bot, game.chat_id, message)

    if game.autumn:
        update_centers(bot, game)
    else:
        game.advance()
        turn_start(bot, game)


def check_victory(bot, game):
    if len(game.players) == 1:
        winner = next(p for p in game.players.values())

    else:
        try:
            winner = next(p for p in game.players.values()
                          if len(owned(game.board, p.nation)) >= 18)

        except StopIteration:
            return False

    send_with_retry(
        bot, winner.id, "<b>You won!</b>",
        parse_mode=ParseMode.HTML)

    send_with_retry(
        bot, game.chat_id,
        "<b>{} ({}) wins!</b>".format(
            winner.nation, winner.get_handle(bot, game.chat_id)),
        parse_mode=ParseMode.HTML)

    del games[game.chat_id]

    return True


def distance_from_home(t, nation):
    distances = full_graph.distances(t)
    return min(distances[hsc] for hsc in home_centers[nation])


def auto_disband(board, nation, n):
    candidates = sorted(
        (
            distance_from_home(t, nation),
            0 if board[t].kind == "F" else 1,
            t.upper(),
            t
        )

        for t in occupied(board, nation)
    )

    disbanding = map(itemgetter(3), candidates[:n])

    for t in disbanding:
        board[t].occupied = None
        board[t].kind = None
        board[t].coast = None


def update_centers(bot, game):
    game.state = "BUILDING_PHASE"

    send_with_retry(bot, game.chat_id, "Updating supply centers...")

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

        units = occupied(game.board, n)
        centers = owned(game.board, n)

        if p and not centers:
            for t in units:
                game.board[t].occupied = None
                game.board[t].kind = None
                game.board[t].coast = None

            send_with_retry(bot, p.id, "You lost!")
            send_with_retry(
                bot, game.chat_id, "{} ({}) was eliminated".format(
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
                               - occupied(game.board))

            p.units_delta = min(
                centers_n - units_n, len(p.units_options))

        p.units_done = False
        p.units_choices = []
        p.ready = not p.units_delta

        if not p.ready:
            show_units_menu(bot, game, p)

    units_ready_check(bot, game)


def show_units_menu(bot, game, player):
    if player.units_disbanding:
        send_with_retry(
            bot, player.id,
            "Supply centers have been updated.\n"
            "You have to disband {} of your units".format(
                player.units_delta))

        show_disband_prompt(bot, game, player)

    else:
        send_with_retry(
            bot, player.id,
            "Supply centers have been updated.\n"
            "You can build up to {} new units".format(
                player.units_delta))

        show_build_prompt(bot, game, player)


def show_disband_prompt(bot, game, player):
    if not player.units_delta:
        message = ("These units will be disbanded: {}\n"
                   "Are you sure?".format(
                        ", ".join(player.units_choices)))

        keyboard = [["Yes", "No"]]

    else:
        keyboard = make_grid(sorted(
            player.units_options.difference(player.units_choices),
            key=str.lower))

        if not player.units_choices:
            message = "Which unit should be disbanded{}?".format(
                " first" if len(player.units_options) > 1 else "")

        else:
            message = "Disbanding {}. Who else?".format(
                ", ".join(player.units_choices))

            keyboard.append(["Back"])

    send_with_retry(bot, player.id, message, reply_markup=RKM(keyboard))


def format_build(choices):
    s = ""

    for t, k, c in choices:
        s += "{} in {}{}\n".format(
            "An army" if k == "A" else "A fleet", t, c or "")

    return s


def show_build_prompt(bot, game, player):
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
            key=str.lower))

        keyboard.append(["Done"])

        if not player.units_choices:
            message = "Where do you want to build?"

        else:
            message = ("Currently building:\n\n"
                       + format_build(player.units_choices)
                       + "\nWhat else?")

            keyboard.append(["Back"])

    send_with_retry(bot, player.id, message, reply_markup=RKM(keyboard))


def disband_msg_handler(bot, update, game, player):
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
        send_with_retry(bot, player.id, message)
        return

    show_disband_prompt(bot, game, player)


def build_msg_handler(bot, update, game, player):
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
        send_with_retry(bot, player.id, message)
        return

    show_build_prompt(bot, game, player)


def units_ready_check(bot, game):
    if all(p.ready for p in game.players.values()):
        execute_builds_and_disbands(bot, game)


def execute_builds_and_disbands(bot, game):
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


def generic_group_msg_handler(bot, update):
    try:
        game = games[update.message.chat.id]
    except KeyError:
        return

    if game.state == "CHOOSING_YEAR":
        year_msg_handler(bot, update, game)


def generic_private_msg_handler(bot, update):
    player_id = update.message.chat.id

    try:
        game = game_by_player(player_id)
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


def error_handler(bot, update, error):
    logger.warning("Got \"%s\" error while processing update:\n%s\n", error, pprint.pformat(update))


def send_with_retry(bot, *args, **kwargs):
    for t in range(1, 31):
        try:
            bot.send_message(*args, **kwargs)
        except TimedOut as e:
            print("Retry " + t)
            time.sleep(t)
        else:
            break

    else:
        raise e


def reply_text_with_retry(update, *args, **kwargs):
    for t in range(1, 31):
        try:
            update.message.reply_text(*args, **kwargs)
        except TimedOut as e:
            print("Retry " + t)
            time.sleep(t)
        else:
            break

    else:
        raise e


def main():
    try:
        f = open("token", "r")
    except OSError:
        print("Token file not found")
        exit(1)

    with f:
        token = f.read().strip()

    updater = Updater(token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start",     start_cmd))
    dp.add_handler(CommandHandler("help",      help_cmd))
    dp.add_handler(CommandHandler("newgame",   newgame_cmd))
    dp.add_handler(CommandHandler("closegame", closegame_cmd))
    dp.add_handler(CommandHandler("startgame", startgame_cmd))
    dp.add_handler(CommandHandler("join",      join_cmd))
    dp.add_handler(CommandHandler("new",       new_cmd))
    dp.add_handler(CommandHandler("delete",    delete_cmd))
    dp.add_handler(CommandHandler("ready",     ready_cmd))
    dp.add_handler(CommandHandler("unready",   unready_cmd))

    #dp.add_handler(CallbackQueryHandler(newgame_cbh,      pattern = "NEWGAME_.*"))
    dp.add_handler(CallbackQueryHandler(nations_menu_cbh, pattern="NATION_.*"))

    dp.add_handler(MessageHandler(
        Filters.text & Filters.group, generic_group_msg_handler))
    dp.add_handler(MessageHandler(
        Filters.text & Filters.private, generic_private_msg_handler))

    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()


