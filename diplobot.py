#!/usr/bin/env python3

  ############################################################################
  # diplobot.py - play Diplomacy through Telegram                            #
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

import re
import random
import logging
from copy import copy
from itertools import count, chain

from telegram import TelegramError, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram.error import BadRequest

from insensitive_list import InsensitiveList
from graph import Graph


try:
    f = open("token", "r")
except OSError:
    print("Token file not found")
    exit(1)

with f:
    token = f.read().strip()

logging.basicConfig(format = "%(asctime)s - %(name)s - %(levelname)s %(message)s", level = logging.INFO)
logger = logging.getLogger(__name__)


nations = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]

sea_graph = Graph({
    "Alb" : {"ADR", "Gre", "ION", "Tri"},
    "Ank" : {"Arm", "BLA", "Con"},
    "Apu" : {"ADR", "ION", "Nap", "Ven"},
    "Arm" : {"Ank", "BLA", "Sev"},
    "Bel" : {"ENG", "Hol", "NTH", "Pic"},
    "Ber" : {"BAL", "Kie", "Pru"},
    "Bre" : {"ENG", "Gas", "MAO", "Pic"},
    "Bul(NC)" : {"BLA", "Con", "Rum"},
    "Bul(SC)" : {"AEG", "Con", "Gre"},
    "Cly" : {"Edi", "Lvp", "NAO", "NWG"},
    "Con" : {"AEG", "Ank", "BLA", "Bul(NC)", "Bul(SC)", "Smy"},
    "Den" : {"BAL", "HEL", "Kie", "NTH", "SKA", "Swe"},
    "Edi" : {"Cly", "NTH", "NWG", "Yor"},
    "Fin" : {"BOT", "StP(SC)", "Swe"},
    "Gas" : {"Bre", "MAO", "Spa(NC)"},
    "Gre" : {"AEG", "Alb", "Bul(SC)", "ION"},
    "Hol" : {"Bel", "HEL", "Kie", "NTH"},
    "Kie" : {"BAL", "Ber", "Den", "HEL", "Hol"},
    "Lon" : {"ENG", "NTH", "Wal", "Yor"},
    "Lvn" : {"BAL", "BOT", "Pru", "StP(SC)"},
    "Lvp" : {"Cly", "IRI", "NAO", "Wal"},
    "Mar" : {"LYO", "Pie", "Spa(SC)"},
    "NAf" : {"MAO", "Tun", "WES"},
    "Nap" : {"Apu", "ION", "Rom", "TYS"},
    "Nwy" : {"BAR", "NTH", "NWG", "SKA", "StP(NC)", "Swe"},
    "Pic" : {"Bel", "Bre", "ENG"},
    "Pie" : {"LYO", "Mar", "Tus"},
    "Por" : {"MAO", "Spa(NC)", "Spa(SC)"},
    "Pru" : {"BAL", "Ber", "Lvn"},
    "Rom" : {"Nap", "Tus", "TYS"},
    "Rum" : {"BLA", "Bul(NC)", "Sev"},
    "Sev" : {"Arm", "BLA", "Rum"},
    "Smy" : {"AEG", "Con", "EAS", "Syr"},
    "Spa(NC)" : {"Gas", "MAO", "Por"},
    "Spa(SC)" : {"LYO", "MAO", "Mar", "Por", "WES"},
    "StP(NC)" : {"BAR", "Nwy"},
    "StP(SC)" : {"BOT", "Fin", "Lvn"},
    "Swe" : {"BAL", "BOT", "Den", "Fin", "Nwy", "SKA"},
    "Syr" : {"EAS", "Smy"},
    "Tri" : {"ADR", "Alb", "Ven"},
    "Tun" : {"ION", "NAf", "TYS", "WES"},
    "Tus" : {"LYO", "Pie", "Rom", "TYS"},
    "Ven" : {"ADR", "Apu", "Tri"},
    "Wal" : {"ENG", "IRI", "Lon", "Lvp"},
    "Yor" : {"Edi", "Lon", "NTH"},
    "AEG" : {"Bul(SC)", "Con", "EAS", "Gre", "ION", "Smy"},
    "ADR" : {"Alb", "Apu", "ION", "Tri", "Ven"},
    "BAL" : {"Ber", "BOT", "Den", "Kie", "Lvn", "Pru", "Swe"},
    "BAR" : {"NWG", "Nwy", "StP(NC)"},
    "BLA" : {"Ank", "Arm", "Bul(NC)", "Con", "Rum", "Sev"},
    "BOT" : {"BAL", "Fin", "Lvn", "StP(SC)", "Swe"},
    "EAS" : {"AEG", "ION", "Smy", "Syr"},
    "ENG" : {"Bel", "Bre", "IRI", "Lon", "MAO", "NTH", "Pic", "Wal"},
    "HEL" : {"Den", "Hol", "Kie", "NTH"},
    "ION" : {"ADR", "AEG", "Alb", "Apu", "EAS", "Gre", "Nap", "Tun", "TYS"},
    "IRI" : {"ENG", "Lvp", "MAO", "NAO", "Wal"},
    "LYO" : {"Mar", "Pie", "Spa(SC)", "Tus", "TYS", "WES"},
    "MAO" : {"Bre", "ENG", "Gas", "IRI", "NAf", "NAO", "Por", "Spa(NC)", "Spa(SC)", "WES"},
    "NAO" : {"Cly", "IRI", "Lvp", "MAO", "NWG"},
    "NTH" : {"Bel", "Den", "Edi", "ENG", "HEL", "Hol", "Lon", "NWG", "Nwy", "SKA", "Yor"},
    "NWG" : {"BAR", "Cly", "Edi", "NAO", "NTH", "Nwy"},
    "SKA" : {"Den", "NTH", "Nwy", "Swe"},
    "TYS" : {"ION", "LYO", "Nap", "Rom", "Tun", "Tus", "WES"},
    "WES" : {"LYO", "MAO", "NAf", "Spa(SC)", "Tun", "TYS"}
})

land_graph = Graph({
    "Alb" : {"Gre", "Ser", "Tri"},
    "Ank" : {"Arm", "Con", "Smy"},
    "Apu" : {"Nap", "Rom", "Ven"},
    "Arm" : {"Ank", "Sev", "Smy", "Syr"},
    "Bel" : {"Bur", "Hol", "Pic", "Ruh"},
    "Ber" : {"Kie", "Mun", "Pru", "Sil"},
    "Boh" : {"Gal", "Mun", "Sil", "Tyr", "Vie"},
    "Bre" : {"Gas", "Par", "Pic"},
    "Bud" : {"Gal", "Rum", "Ser", "Tri", "Vie"},
    "Bul" : {"Con", "Gre", "Rum", "Ser"},
    "Bur" : {"Bel", "Gas", "Mar", "Mun", "Par", "Pic", "Ruh"},
    "Cly" : {"Edi", "Lvp"},
    "Con" : {"Ank", "Bul", "Smy"},
    "Den" : {"Kie", "Swe"},
    "Edi" : {"Cly", "Lvp", "Yor"},
    "Fin" : {"Nwy", "StP", "Swe"},
    "Gal" : {"Boh", "Bud", "Rum", "Sil", "Ukr", "Vie", "War"},
    "Gas" : {"Bre", "Bur", "Mar", "Par", "Spa"},
    "Gre" : {"Alb", "Bul", "Ser"},
    "Hol" : {"Bel", "Kie", "Ruh"},
    "Kie" : {"Ber", "Den", "Hol", "Mun", "Ruh"},
    "Lon" : {"Wal", "Yor"},
    "Lvn" : {"Mos", "Pru", "StP", "War"},
    "Lvp" : {"Cly", "Edi", "Wal", "Yor"},
    "Mar" : {"Bur", "Gas", "Pie", "Spa"},
    "Mos" : {"Lvn", "Sev", "StP", "Ukr", "War"},
    "Mun" : {"Ber", "Boh", "Bur", "Kie", "Ruh", "Sil", "Tyr"},
    "NAf" : {"Tun"},
    "Nap" : {"Apu", "Rom"},
    "Nwy" : {"Fin", "StP", "Swe"},
    "Par" : {"Bre", "Bur", "Gas", "Pic"},
    "Pic" : {"Bel", "Bre", "Bur", "Par"},
    "Pie" : {"Mar", "Tus", "Tyr", "Ven"},
    "Por" : {"Spa"},
    "Pru" : {"Ber", "Lvn", "Sil", "War"},
    "Rom" : {"Apu", "Nap", "Tus", "Ven"},
    "Ruh" : {"Bel", "Bur", "Hol", "Kie", "Mun"},
    "Rum" : {"Bud", "Bul", "Gal", "Ser", "Sev", "Ukr"},
    "Ser" : {"Alb", "Bud", "Bul", "Gre", "Rum", "Tri"},
    "Sev" : {"Arm", "Mos", "Rum", "Ukr"},
    "Sil" : {"Ber", "Boh", "Gal", "Mun", "Pru", "War"},
    "Smy" : {"Ank", "Arm", "Con", "Syr"},
    "Spa" : {"Gas", "Mar", "Por"},
    "StP" : {"Fin", "Lvn", "Mos", "Nwy"},
    "Swe" : {"Den", "Fin", "Nwy"},
    "Syr" : {"Arm", "Smy"},
    "Tri" : {"Alb", "Bud", "Ser", "Tyr", "Ven", "Vie"},
    "Tun" : {"NAf"},
    "Tus" : {"Pie", "Rom", "Ven"},
    "Tyr" : {"Boh", "Mun", "Pie", "Tri", "Ven", "Vie"},
    "Ukr" : {"Gal", "Mos", "Rum", "Sev", "War"},
    "Ven" : {"Apu", "Pie", "Rom", "Tri", "Tus", "Tyr"},
    "Vie" : {"Boh", "Bud", "Gal", "Tri", "Tyr"},
    "Wal" : {"Lon", "Lvp", "Yor"},
    "War" : {"Gal", "Lvn", "Mos", "Pru", "Sil", "Ukr"},
    "Yor" : {"Edi", "Lon", "Lvp", "Wal"}
})


def strip_coast(t):
    return t[:3]


territories = {strip_coast(t)
    for t in chain(land_graph.vertices(), sea_graph.vertices())}

terr_names = InsensitiveList(sorted({strip_coast(t) for t in territories}))

offshore = {
    "AEG", "ADR", "BAL", "BAR", "BLA",
    "BOT", "EAS", "ENG", "HEL", "ION",
    "IRI", "LYO", "MAO", "NAO", "NTH",
    "NWG", "SKA", "TYS", "WES"
}

coast = sea_graph.vertices() - offshore

bla_coast  = {strip_coast(t) for t in sea_graph.neighbors({"BLA"})}
bal_coast  = {strip_coast(t) for t in sea_graph.neighbors({"BAL", "BOT"})}
main_coast = {strip_coast(t)
    for t in sea_graph.neighbors(offshore - {"BLA", "BAL", "BOT"})}

coasts = (bla_coast, bal_coast, main_coast)

split_coasts = {"Bul", "Spa", "StP"}

prod_centers = {
    "Ank", "Bel", "Ber", "Bre", "Bud",
    "Bul", "Con", "Den", "Edi", "Gre",
    "Hol", "Kie", "Lon", "Lvp", "Mar",
    "Mos", "Mun", "Nap", "Nwy", "Par",
    "Por", "Rom", "Rum", "Ser", "Sev",
    "Smy", "Spa", "StP", "Swe", "Tri",
    "Tun", "Ven", "Vie", "War"
}


class Territory:
    def __init__(self, owner=None, occupied=None, kind=None, coast=None):
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

    def __lt__(self, other):
        return str(self) < str(other)


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
        self.terr_delete = False

    def __bool__(self):
        return self.building is not None

    def new(self):
        self.building = Order()
        self.terrs = set()
        self.terr_complete = False
        self.terr_delete = False

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
        if (self.board[self.terr].kind != 'F'
            or self.building.targ not in split_coasts):

            return True

        i = 0

        for c in ("(NC)", "(SC)"):
            try:
                if self.terr in sea_graph.neighbors((self.building.targ + c,)):
                    self.coast = c
                    i += 1

            except KeyError:
                pass

        if i != 1:
            self.coast = None
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
                raise ValueError

            self.terr_complete = True
            return

        if s == "DELETE":
            if not self.terrs:
                raise ValueError

            self.terr_delete = True
            return

        if s == "ADD":
            self.terr_delete = False
            return

        if self.terr_delete:
            try:
                self.terrs.remove(s)
            except KeyError:
                raise ValueError
        else:
            try:
                t = terr_names.match_case(s)

            except KeyError:
                raise ValueError

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

    def register_targ(self, s):
        try:
            t = terr_names.match_case(s)
        except KeyError:
            raise ValueError

        self.validate_targ(t)

        self.building.targ = t

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
                    return

            elif self.terr_complete:
                self.terrs = set()
                self.terr_complete = False
                return

        else:
            raise IndexError

    def push(self, s):
        s = s.strip().upper()

        ntf = self.next_to_fill()

        if s == "BACK":
            self.back()

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


class Player:
    def __init__(self, player_id, board):
        self.id = player_id
        self._nation = None
        self._orders = set()
        self.builder = OrderBuilder(board, self._orders)
        self.ready = False
        self.deleting = False

    def set_nation(self, nation):
        self._nation = nation
        self.builder.nation = nation

    def set_orders(self, orders):
        self._orders = orders
        self.builder.orders = orders

    nation = property(lambda self: self._nation, set_nation)
    orders = property(lambda self: self._orders, set_orders)

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
        self.status = "NEW"
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
            bot.send_message(self.chat_id, handle + " joined the game")

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
    if update.message.chat.type != 'group':
        update.message.reply_text("This command can only be used in a group chat")
        raise HandlerGuard


def private_chat_guard(update):
    if update.message.chat.type != 'private':
        update.message.reply_text("This command can only be used in a private chat")
        raise HandlerGuard


def game_exists_guard(update):
    if update.message.chat.id not in games:
        update.message.reply_text("There is no game currently running in this chat\n"
                                  "Start one with /newgame!")
        raise HandlerGuard

def player_in_game_guard(update):
    try:
        return game_by_player(update.message.chat.id)
    except KeyError:
        update.message.reply_text("You need to join a game to use this command")
        raise HandlerGuard


def game_status_guard(update, game, status):
    if game.status != status:
        update.message.reply_text("You can't use this command right now")
        raise HandlerGuard


def player_not_ready_guard(update, player):
    if player.ready:
        update.message.reply_text(
            "You have already committed you orders. Withdraw with /unready", quote=False)
        raise HandlerGuard


def player_ready_guard(update, player):
    if not player.ready:
        update.message.reply_text("You have not committed your orders yet", quote=False)
        raise HandlerGuard


def player_not_building_order_guard(update, player):
    if player.builder:
        update.message.reply_text("You have an order to complete first", quote=False)
        raise HandlerGuard


def player_not_deleting_orders_guard(update, player):
    if player.deleting:
        update.message.reply_text("You have to tell me what orders to delete first (back to abort)", quote=False)
        raise HandlerGuard


## Handlers
###########


def start_cmd(bot, update):
    update.message.reply_text("DiploBot started!", quote=False)


def help_cmd(bot, update):
    update.message.reply_text("There's no help right now",
                              quote=False)


def newgame(bot, chat_id, from_id):
    global games

    new_game = Game(chat_id)
    games[chat_id] = new_game

    bot.send_message(chat_id,
                     "A new <i>Diplomacy</i>  game is starting!\n"
                     "Join now with /join",
                     parse_mode = ParseMode.HTML)

    handle = new_game.add_player(from_id, bot).get_handle(bot, chat_id)


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

    update.message.reply_text("A game is already running in this chat", quote=False)

    #TODO: vote?

    #game = games[chat_id]
    #
    #if from_id == game.adj_id:
    #    newgame_yes = InlineKeyboardButton("Yes", callback_data="NEWGAME_YES")
    #    newgame_no  = InlineKeyboardButton("No", callback_data="NEWGAME_NO")

    #    newgame_yesno = InlineKeyboardMarkup([[newgame_yes, newgame_no]])

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
    global games

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
        bot.send_message(p.id, "Game closed")

    update.message.reply_text("Game closed", quote=False)


def join_cmd(bot, update):
    try:
        group_chat_guard(update)
        game_exists_guard(update)
    except HandlerGuard:
        return

    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    handle  = "@" + update.message.from_user.username

    game = games[chat_id]

    if game.status != "NEW":
        update.message.reply_text(handle + " you can't join right now", quote=False)
        return

    if user_id in game.players:
        update.message.reply_text(handle + " you already have joined this game", quote=False)
        return

    for g in games.values():
        if user_id in g.players:
            update.message.reply_text(handle + " you are in another game already", quote=False)
            return

    game.add_player(user_id, bot)

    if not game.is_full():
        return

    update.message.reply_text("All the players have joined", quote=False)
    startgame(bot, game)


def startgame_cmd(bot, update):
    try:
        game_exists_guard(update)
    except HandlerGuard:
        return

    game = games[update.message.chat.id]

    #TODO: uncomment this!
    #if len(game.players) < 2:
    #    update.message.reply_text("At least two people have to join before the game can start", quote=False)
    #    return

    startgame(bot, game)


def startgame(bot, game):
    game.status = "CHOOSING_NATIONS"

    bot.send_message(game.chat_id, "The game will begin shortly...")
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

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(n, callback_data="NATION_" + n)]
        for n in available
    ])

    handle = player.get_handle(bot, game.chat_id)
    message = bot.send_message(
        game.chat_id, handle + " choose a nation", reply_markup=keyboard)

    game.assigning = player.id
    game.assigning_message = message


def nations_menu_cbh(bot, update):
    error = False

    try:
        game = games[update.callback_query.message.chat.id]
    except KeyError:
        error = True

    if error or game.status != "CHOOSING_NATIONS":
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

    try:
        update.callback_query.message.edit_reply_markup()
        update.callback_query.message.edit_text(
            "{} will play as {}".format(handle, player.nation))
    except TelegramError:
        pass

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
    bot.send_message(game.chat_id, "What year should the game begin in?")

    game.status = "CHOOSING_YEAR"


year_re = re.compile("^(\d*)\s*(AD|BC|CE|BCE)?$", re.IGNORECASE)

def year_msg_handler(bot, update, game):
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


def show_timeout_menu(bot, game):
    game.status = 'CHOOSING_TIMEOUT'

    # TODO: implement this

    game_start(bot, game)


def game_start(bot, game):
    start_message = "<b>Nations have been assigned as follows:</b>\n\n"
    for p in game.players.values():
        handle = p.get_handle(bot, game.chat_id)
        start_message += "    {} as {}\n".format(handle, p.nation)

    start_message += "\nThe year is {}\nLet the game begin!".format(game.printable_year())

    bot.send_message(game.chat_id, start_message, parse_mode="HTML")

    game.status = 'STARTED'

    turn_start(bot, game)


def turn_start(bot, game):
    for p in game.players.values():
        p.reset()
        bot.send_message(p.id, "Awaiting orders for {}".format(game.date()))
        show_command_menu(bot, game, p)


def show_command_menu(bot, game, player):
    message = ""
    for index, order in enumerate(sorted(player.orders), 1):
        message += "{}. {}\n".format(index, str(order)) # TODO: use long formatting

    if message:
        message += "\n"

    message += ("/new -- submit a new order\n"
                "/delete -- withdraw an order\n"
                "/ready -- when you are done")

    bot.send_message(player.id, message)


def new_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "STARTED")

        player = game.players[update.message.chat.id]
        player_not_ready_guard(update, player)
        player_not_building_order_guard(update, player)
        player_not_deleting_orders_guard(update, player)

    except HandlerGuard:
        return

    player.builder.new()

    show_order_menu(bot, game, player)


def show_order_menu(bot, game, player, ntf=None):
    if not ntf:
        ntf = player.builder.next_to_fill()

    bot.send_message(player.id, "DEBUG: awaiting order data " + ntf) # TODO: send a keyboard


def order_msg_handler(bot, update, game, player):
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


def delete_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "STARTED")

        player = game.players[update.message.chat.id]
        player_not_ready_guard(update, player)
        player_not_building_order_guard(update, player)
        player_not_deleting_orders_guard(update, player)

    except HandlerGuard:
        return

    update.message.reply_text("Which orders do you want to delete? (back to abort)")

    player.deleting = True


parse_delete_num_re = re.compile("^(\d+)$")
parse_delete_range_re = re.compile("^(\d+)\s*-\s*(\d+)$")

def parse_delete_msg(s, n):
    ss = s.split(',')

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
        update.message.reply_text("Invalid input")
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
        game_status_guard(update, game, "STARTED")

        player = game.players[update.message.chat.id]
        player_not_ready_guard(update, player)
        player_not_building_order_guard(update, player)
        player_not_deleting_orders_guard(update, player)

    except HandlerGuard:
        return

    update.message.reply_text("Orders committed. Withdraw with /unready")

    player.ready = True

    ready_check(bot, game)


def unready_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "STARTED")

        player = game.players[update.message.chat.id]
        player_ready_guard(update, player)

    except HandlerGuard:
        return

    update.message.reply_text("Orders withdrawn")

    player.ready = False

    show_command_menu(bot, game, player)


def ready_check(bot, game):
    if all(p.ready for p in game.players.values()):
        adjudicate(bot, game)


def adjudicate(bot, game):
    pass # TODO


def generic_group_msg_handler(bot, update):
    try:
        game = games[update.message.chat.id]
    except KeyError:
        return

    if game.status == "CHOOSING_YEAR":
        year_msg_handler(bot, update, game)


def generic_private_msg_handler(bot, update):
    player_id = update.message.chat.id

    try:
        game = game_by_player(player_id)
    except KeyError:
        return

    player = game.players[player_id]

    if game.status == "STARTED":
        if not player.ready and player.builder:
            order_msg_handler(bot, update, game, player)

        elif not player.ready and player.deleting:
            delete_msg_handler(bot, update, game, player)


def error_handler(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
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
    dp.add_handler(CallbackQueryHandler(nations_menu_cbh, pattern = "NATION_.*"))

    dp.add_handler(MessageHandler(
        Filters.text & Filters.group, generic_group_msg_handler))
    dp.add_handler(MessageHandler(
        Filters.text & Filters.private, generic_private_msg_handler))

    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()


