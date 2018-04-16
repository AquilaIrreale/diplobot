#!/usr/bin/env python3

import re
import random
import logging
from itertools import chain

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


terr_names = InsensitiveList(
    sorted({strip_coast(t) for t in chain(land_graph.vertices(), sea_graph.vertices())}))


terr_names = InsensitiveList([
    "Alb", "Ank", "Apu", "Arm", "Bel", "Ber", "Boh", "Bre",
    "Bud", "Bul", "Bur", "Cly", "Con", "Den", "Edi", "Fin",
    "Gal", "Gas", "Gre", "Hol", "Kie", "Lon", "Lvn", "Lvp",
    "Mar", "Mos", "Mun", "NAf", "Nap", "Nwy", "Par", "Pic",
    "Pie", "Por", "Pru", "Rom", "Ruh", "Rum", "Ser", "Sev",
    "Sil", "Smy", "Spa", "StP", "Swe", "Syr", "Tri",
    "Tun", "Tus", "Tyr", "Ukr", "Ven", "Vie", "Wal", "War",
    "Yor", "AEG", "ADR", "BAL", "BAR", "BLA", "BOT", "EAS",
    "ENG", "HEL", "ION", "IRI", "LYO", "MAO", "NAO", "NTH",
    "NWG", "SKA", "TYS", "WES"
])


class TerrInfo:
    def __init__(self, prod_center=False, is_split=False):
        self.is_split = is_split
        self.prod_center = prod_center


terrinfo = {
    "Alb": TerrInfo(prod_center=False, is_split=False),
    "Ank": TerrInfo(prod_center=True,  is_split=False),
    "Apu": TerrInfo(prod_center=False, is_split=False),
    "Arm": TerrInfo(prod_center=False, is_split=False),
    "Bel": TerrInfo(prod_center=True,  is_split=False),
    "Ber": TerrInfo(prod_center=True,  is_split=False),
    "Boh": TerrInfo(prod_center=False, is_split=False),
    "Bre": TerrInfo(prod_center=True,  is_split=False),
    "Bud": TerrInfo(prod_center=True,  is_split=False),
    "Bul": TerrInfo(prod_center=True,  is_split=True),
    "Bur": TerrInfo(prod_center=False, is_split=False),
    "Cly": TerrInfo(prod_center=False, is_split=False),
    "Con": TerrInfo(prod_center=True,  is_split=False),
    "Den": TerrInfo(prod_center=True,  is_split=False),
    "Edi": TerrInfo(prod_center=True,  is_split=False),
    "Fin": TerrInfo(prod_center=False, is_split=False),
    "Gal": TerrInfo(prod_center=False, is_split=False),
    "Gas": TerrInfo(prod_center=False, is_split=False),
    "Gre": TerrInfo(prod_center=True,  is_split=False),
    "Hol": TerrInfo(prod_center=True,  is_split=False),
    "Kie": TerrInfo(prod_center=True,  is_split=False),
    "Lon": TerrInfo(prod_center=True,  is_split=False),
    "Lvn": TerrInfo(prod_center=False, is_split=False),
    "Lvp": TerrInfo(prod_center=True,  is_split=False),
    "Mar": TerrInfo(prod_center=True,  is_split=False),
    "Mos": TerrInfo(prod_center=True,  is_split=False),
    "Mun": TerrInfo(prod_center=True,  is_split=False),
    "NAf": TerrInfo(prod_center=False, is_split=False),
    "Nap": TerrInfo(prod_center=True,  is_split=False),
    "Nwy": TerrInfo(prod_center=True,  is_split=False),
    "Par": TerrInfo(prod_center=True,  is_split=False),
    "Pic": TerrInfo(prod_center=False, is_split=False),
    "Pie": TerrInfo(prod_center=False, is_split=False),
    "Por": TerrInfo(prod_center=True,  is_split=False),
    "Pru": TerrInfo(prod_center=False, is_split=False),
    "Rom": TerrInfo(prod_center=True,  is_split=False),
    "Ruh": TerrInfo(prod_center=False, is_split=False),
    "Rum": TerrInfo(prod_center=True,  is_split=False),
    "Ser": TerrInfo(prod_center=True,  is_split=False),
    "Sev": TerrInfo(prod_center=True,  is_split=False),
    "Sil": TerrInfo(prod_center=False, is_split=False),
    "Smy": TerrInfo(prod_center=True,  is_split=False),
    "Spa": TerrInfo(prod_center=True,  is_split=True),
    "StP": TerrInfo(prod_center=True,  is_split=True),
    "Swe": TerrInfo(prod_center=True,  is_split=False),
    "Syr": TerrInfo(prod_center=False, is_split=False),
    "Tri": TerrInfo(prod_center=True,  is_split=False),
    "Tun": TerrInfo(prod_center=True,  is_split=False),
    "Tus": TerrInfo(prod_center=False, is_split=False),
    "Tyr": TerrInfo(prod_center=False, is_split=False),
    "Ukr": TerrInfo(prod_center=False, is_split=False),
    "Ven": TerrInfo(prod_center=True,  is_split=False),
    "Vie": TerrInfo(prod_center=True,  is_split=False),
    "Wal": TerrInfo(prod_center=False, is_split=False),
    "War": TerrInfo(prod_center=True,  is_split=False),
    "Yor": TerrInfo(prod_center=False, is_split=False),
    "AEG": TerrInfo(prod_center=False, is_split=False),
    "ADR": TerrInfo(prod_center=False, is_split=False),
    "BAL": TerrInfo(prod_center=False, is_split=False),
    "BAR": TerrInfo(prod_center=False, is_split=False),
    "BLA": TerrInfo(prod_center=False, is_split=False),
    "BOT": TerrInfo(prod_center=False, is_split=False),
    "EAS": TerrInfo(prod_center=False, is_split=False),
    "ENG": TerrInfo(prod_center=False, is_split=False),
    "HEL": TerrInfo(prod_center=False, is_split=False),
    "ION": TerrInfo(prod_center=False, is_split=False),
    "IRI": TerrInfo(prod_center=False, is_split=False),
    "LYO": TerrInfo(prod_center=False, is_split=False),
    "MAO": TerrInfo(prod_center=False, is_split=False),
    "NAO": TerrInfo(prod_center=False, is_split=False),
    "NTH": TerrInfo(prod_center=False, is_split=False),
    "NWG": TerrInfo(prod_center=False, is_split=False),
    "SKA": TerrInfo(prod_center=False, is_split=False),
    "TYS": TerrInfo(prod_center=False, is_split=False),
    "WES": TerrInfo(prod_center=False, is_split=False)
}

prod_centers = {t for t in terrinfo if terrinfo[t].prod_center}


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
        "Mos": Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="F"),
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
        "StP": Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="F",  coast="SC"),
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
    def __init__(self, board):
        self.board = board
        self.kind = None
        self.terrs = set()
        self.terr_complete = False
        self.terr_delete = False
        self.orig = None
        self.targ = None
        self.coast = None
        self.via_c = None

    def get_terr(self):
        try:
            return next(iter(self.terrs))
        except StopIteration:
            return None

    def set_terr(self, x):
        self.terrs = {x}

    def del_terr(self):
        self.terrs = set()

    terr = property(get_terr, set_terr, del_terr)

    def __str__(self):
        coast = "({})".format(self.coast) if self.coast else ""
        via_c = " C" if self.via_c else ""

        try:
            if self.next_to_fill() != "DONE":
                return "Incomplete order"

            if self.kind == "HOLD":
                return "{} H".format(self.terr)

            if self.kind == "MOVE":
                return "{}-{}{}{}".format(self.terr, self.targ, coast, via_c)

            if self.kind == "SUPH":
                return "{} S {}".format(", ".join(self.terrs), self.targ)

            if self.kind == "SUPM":
                return "{} S {}-{}".format(", ".join(self.terrs), self.orig, self.targ)

            if self.kind == "CONV":
                return "{} C {}-{}".format(", ".join(self.terrs), self.orig, self.targ)

        except StopIteration:
            return "Invalid order (empty terr)"

        return "Invalid order (unknown kind)"

    def next_to_fill(self):
        if self.kind is None:
            return "KIND"

        if not self.terr_complete:
            return "TERR" if not self.terr_delete else "TERR_DELETE"

        if self.kind == "HOLD":
            return "DONE"

        if self.orig is None and self.kind in {"SUPM", "CONV"}:
            return "ORIG"

        if self.targ is None:
            return "TARG"

        if self.kind == "MOVE":
            fleet = self.board[self.terr].kind == "F"
            split = terrinfo[self.targ].is_split

            if not fleet and self.via_c is None:
                return "VIAC"
            elif fleet and self.coast is None and split:
                return "COAST"

        return "DONE"

    kinds = {
        "HOLD":            "HOLD",
        "MOVE (ATTACK)":   "MOVE",
        "MOVE":            "MOVE",
        "ATTACK":          "MOVE",
        "SUPPORT HOLD":    "SUPH",
        "SUPPORT TO HOLD": "SUPH",
        "SUPPORT A HOLD":  "SUPH",
        "SUPPORT MOVE":    "SUPM",
        "SUPPORT TO MOVE": "SUPM",
        "SUPPORT A MOVE":  "SUPM",
        "CONVOY":          "CONV"
    }

    kind_codes = set(kinds.values())

    def register_kind(self, s):
        try:
            self.kind = self.kinds[s]
        except KeyError:
            pass
        else:
            return

        if s in self.kind_codes:
            self.kind = s
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

        if not self.terr_delete:
            try:
                s = terr_names.match_case(s)

            except KeyError:
                raise ValueError

            else:
                self.terrs.add(s)

                if self.kind not in {"SUPH", "SUPM", "CONV"}:
                    self.terr_complete = True
        else:
            try:
                self.terrs.remove(s)
            except KeyError:
                raise ValueError

    def register_terr(self, which, s):
        try:
            s = terr_names.match_case(s)

        except KeyError:
            raise ValueError

        else:
            setattr(self, which, s)

    def register_viac(self, s):
        if s in {"YES", "Y"}:
            self.via_c = True
        elif s in {"NO", "N"}:
            self.via_c = False
        else:
            raise ValueError

    def register_coast(self, s):
        if s in {"NC", "(NC)", "NORTH", "NORTH COAST"}:
            self.coast = "NC"
        elif s in {"SC", "(SC)", "SOUTH", "SOUTH COAST"}:
            self.coast = "SC"
        else:
            raise ValueError

    actions = {
        "KIND":  lambda self, s: self.register_kind(s),
        "TERR":  lambda self, s: self.register_terr_list(s),
        "ORIG":  lambda self, s: self.register_terr("orig", s),
        "TARG":  lambda self, s: self.register_terr("targ", s),
        "VIAC":  lambda self, s: self.register_viac(s),
        "COAST": lambda self, s: self.register_coast(s)
    }

    back_attrs = ["via_c", "coast", "targ", "orig", "terrs", "kind"]

    def back(self):
        for attr in self.back_attrs:
            if attr != "terrs" and getattr(self, attr) is not None:
                setattr(self, attr, None)
                return

            if self.terr_complete:
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



    # TODO: maybe look into coroutines?
    # TODO: make saner!!
    #def push_old(self, s):
    #    if self.kind is None:
    #        if s.upper() in Order.kinds.values():
    #            self.kind = s.upper()
    #            return

    #        try:
    #            self.kind = Order.kinds[s.upper()]
    #        except KeyError:
    #            raise ValueError

    #    elif not self.terr_complete:
    #        if s in territories:
    #            self.terr.append(territories.matchCase(s))
    #            if self.kind != "CONV":
    #                self.terr_complete = True
    #        elif s.upper() == "DONE" and len(self.terr) >= 1:
    #            self.terr.sort(key=str.lower)
    #            self.terr_complete = True
    #        else:
    #            raise ValueError

    #    elif self.orig is None and self.kind in {"CONV", "SUPM"}:
    #        if s in territories:
    #            self.orig = territories.matchCase(s)
    #        else:
    #            raise ValueError

    #    elif self.targ is None:
    #        if s in territories:
    #            self.targ = territories.matchCase(s)
    #        else:
    #            raise ValueError





class Player:
    def __init__(self, player_id):
        self.id = player_id
        self.nation = None
        self.orders = []
        self.building = None
        self.ready = False

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
        player = Player(player_id)
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
        update.message.reply_text("You have already submitted you orders", quote=False)
        raise HandlerGuard


def player_not_building_order_guard(update, player):
    if player.building is not None:
        update.message.reply_text("You have an order to complete first", quote=False)
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
    try:
        game = games[update.callback_query.message.chat.id]
    except KeyError:
        update.callback_query.answer("Something went wrong")
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
    except BadRequest:
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
        p.orders = []
        p.ready = False
        bot.send_message(p.id, "Awaiting orders for {}".format(game.date()))
        show_command_menu(bot, game, p)


def show_command_menu(bot, game, player):
    message = ""
    orders_range = range(1, len(player.orders)+1)
    for order, index in zip(player.orders, orders_range):
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

    except HandlerGuard:
        return

    player.building = Order(game.board)

    show_order_menu(bot, game, player)


def show_order_menu(bot, game, player, ntf=None):
    if not ntf:
        ntf = player.building.next_to_fill()

    bot.send_message(player.id, "DEBUG: awaiting order data " + ntf) # TODO: send a keyboard


def order_msg_handler(bot, update, game, player):
    try:
        ntf = player.building.push(update.message.text)
    except (ValueError, IndexError):
        update.message.reply_text("Invalid input")
        return

    if ntf == "DONE":
        player.orders.append(player.building)
        player.building = None
        show_command_menu(bot, game, player)

    else:
        show_order_menu(bot, game, player, ntf)


#def order_msg_handler(bot, update, game):
#    player_id = update.message.chat.id
#    s = update.message.text
#
#    if s.lower() == 'back':
#        if game.curOrder[player_id].next_to_fill() == 'ISARMY':
#            game.curOrder[player_id] = None
#            show_command_menu(bot, game, player_id)
#
#        else:
#            game.curOrder[player_id].rollback()
#            show_order_menu(bot, game, player_id)
#
#        return
#
#    try:
#        game.curOrder[player_id].push(s)
#
#    except ValueError:
#        update.message.reply_text("Error (invalid data - placeholder)", quote=False)
#        return
#
#    if game.curOrder[player_id].next_to_fill() == "DONE":
#        game.orders[player_id].append(game.curOrder[playerId])
#        game.curOrder[player_id] = None
#        show_command_menu(bot, game, player_id)
#
#    else:
#        show_order_menu(bot, game, player_id)


def delete_cmd(bot, update):
    pass


def ready_cmd(bot, update):
    try:
        private_chat_guard(update)

        game = player_in_game_guard(update)
        game_status_guard(update, game, "STARTED")

        player = game.players[update.message.chat.id]
        player_not_ready_guard(update, player, False)
        player_not_building_order_guard(update, player, False)

    except HandlerGuard:
        return

    player.ready = True

    ready_check(bot, game)


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

    if (game.status == "STARTED"
        and not player.ready
        and player.building is not None):

        order_msg_handler(bot, update, game, player)


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


