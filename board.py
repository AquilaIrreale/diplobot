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


from copy import copy
from itertools import chain

from insensitive_list import InsensitiveList
from graph import Graph


nations = {"AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"}

sea_graph = Graph({
    "Alb"     : {"ADR", "Gre", "ION", "Tri"},
    "Ank"     : {"Arm", "BLA", "Con"},
    "Apu"     : {"ADR", "ION", "Nap", "Ven"},
    "Arm"     : {"Ank", "BLA", "Sev"},
    "Bel"     : {"ENG", "Hol", "NTH", "Pic"},
    "Ber"     : {"BAL", "Kie", "Pru"},
    "Bre"     : {"ENG", "Gas", "MAO", "Pic"},
    "Bul(NC)" : {"BLA", "Con", "Rum"},
    "Bul(SC)" : {"AEG", "Con", "Gre"},
    "Cly"     : {"Edi", "Lvp", "NAO", "NWG"},
    "Con"     : {"AEG", "Ank", "BLA", "Bul(NC)", "Bul(SC)", "Smy"},
    "Den"     : {"BAL", "HEL", "Kie", "NTH", "SKA", "Swe"},
    "Edi"     : {"Cly", "NTH", "NWG", "Yor"},
    "Fin"     : {"BOT", "StP(SC)", "Swe"},
    "Gas"     : {"Bre", "MAO", "Spa(NC)"},
    "Gre"     : {"AEG", "Alb", "Bul(SC)", "ION"},
    "Hol"     : {"Bel", "HEL", "Kie", "NTH"},
    "Kie"     : {"BAL", "Ber", "Den", "HEL", "Hol"},
    "Lon"     : {"ENG", "NTH", "Wal", "Yor"},
    "Lvn"     : {"BAL", "BOT", "Pru", "StP(SC)"},
    "Lvp"     : {"Cly", "IRI", "NAO", "Wal"},
    "Mar"     : {"LYO", "Pie", "Spa(SC)"},
    "NAf"     : {"MAO", "Tun", "WES"},
    "Nap"     : {"Apu", "ION", "Rom", "TYS"},
    "Nwy"     : {"BAR", "NTH", "NWG", "SKA", "StP(NC)", "Swe"},
    "Pic"     : {"Bel", "Bre", "ENG"},
    "Pie"     : {"LYO", "Mar", "Tus"},
    "Por"     : {"MAO", "Spa(NC)", "Spa(SC)"},
    "Pru"     : {"BAL", "Ber", "Lvn"},
    "Rom"     : {"Nap", "Tus", "TYS"},
    "Rum"     : {"BLA", "Bul(NC)", "Sev"},
    "Sev"     : {"Arm", "BLA", "Rum"},
    "Smy"     : {"AEG", "Con", "EAS", "Syr"},
    "Spa(NC)" : {"Gas", "MAO", "Por"},
    "Spa(SC)" : {"LYO", "MAO", "Mar", "Por", "WES"},
    "StP(NC)" : {"BAR", "Nwy"},
    "StP(SC)" : {"BOT", "Fin", "Lvn"},
    "Swe"     : {"BAL", "BOT", "Den", "Fin", "Nwy", "SKA"},
    "Syr"     : {"EAS", "Smy"},
    "Tri"     : {"ADR", "Alb", "Ven"},
    "Tun"     : {"ION", "NAf", "TYS", "WES"},
    "Tus"     : {"LYO", "Pie", "Rom", "TYS"},
    "Ven"     : {"ADR", "Apu", "Tri"},
    "Wal"     : {"ENG", "IRI", "Lon", "Lvp"},
    "Yor"     : {"Edi", "Lon", "NTH"},
    "AEG"     : {"Bul(SC)", "Con", "EAS", "Gre", "ION", "Smy"},
    "ADR"     : {"Alb", "Apu", "ION", "Tri", "Ven"},
    "BAL"     : {"Ber", "BOT", "Den", "Kie", "Lvn", "Pru", "Swe"},
    "BAR"     : {"NWG", "Nwy", "StP(NC)"},
    "BLA"     : {"Ank", "Arm", "Bul(NC)", "Con", "Rum", "Sev"},
    "BOT"     : {"BAL", "Fin", "Lvn", "StP(SC)", "Swe"},
    "EAS"     : {"AEG", "ION", "Smy", "Syr"},
    "ENG"     : {"Bel", "Bre", "IRI", "Lon", "MAO", "NTH", "Pic", "Wal"},
    "HEL"     : {"Den", "Hol", "Kie", "NTH"},
    "ION"     : {"ADR", "AEG", "Alb", "Apu", "EAS", "Gre", "Nap", "Tun", "TYS"},
    "IRI"     : {"ENG", "Lvp", "MAO", "NAO", "Wal"},
    "LYO"     : {"Mar", "Pie", "Spa(SC)", "Tus", "TYS", "WES"},
    "MAO"     : {"Bre", "ENG", "Gas", "IRI", "NAf", "NAO", "Por", "Spa(NC)", "Spa(SC)", "WES"},
    "NAO"     : {"Cly", "IRI", "Lvp", "MAO", "NWG"},
    "NTH"     : {"Bel", "Den", "Edi", "ENG", "HEL", "Hol", "Lon", "NWG", "Nwy", "SKA", "Yor"},
    "NWG"     : {"BAR", "Cly", "Edi", "NAO", "NTH", "Nwy"},
    "SKA"     : {"Den", "NTH", "Nwy", "Swe"},
    "TYS"     : {"ION", "LYO", "Nap", "Rom", "Tun", "Tus", "WES"},
    "WES"     : {"LYO", "MAO", "NAf", "Spa(SC)", "Tun", "TYS"}
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


full_graph = Graph()

for t1, t2 in chain(sea_graph.edges(), land_graph.edges()):
    full_graph.add_edge((strip_coast(t1), strip_coast(t2)))

territories = {
    strip_coast(t) for t in chain(land_graph.vertices(), sea_graph.vertices())
}

terr_names = InsensitiveList(
    sorted({strip_coast(t) for t in territories}, key=str.casefold))

offshore = {
    "AEG", "ADR", "BAL", "BAR", "BLA",
    "BOT", "EAS", "ENG", "HEL", "ION",
    "IRI", "LYO", "MAO", "NAO", "NTH",
    "NWG", "SKA", "TYS", "WES"
}

coast = {strip_coast(t) for t in sea_graph.vertices() - offshore}

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


class Board(dict):
    def __init__(self):
        super().__init__(self)

        self["Alb"] = Territory()
        self["Ank"] = Territory(owner="TURKEY",  occupied="TURKEY",  kind="F")
        self["Apu"] = Territory()
        self["Arm"] = Territory()
        self["Bel"] = Territory()
        self["Ber"] = Territory(owner="GERMANY", occupied="GERMANY", kind="A")
        self["Boh"] = Territory()
        self["Bre"] = Territory(owner="FRANCE",  occupied="FRANCE",  kind="F")
        self["Bud"] = Territory(owner="AUSTRIA", occupied="AUSTRIA", kind="A")
        self["Bul"] = Territory()
        self["Bur"] = Territory()
        self["Cly"] = Territory()
        self["Con"] = Territory(owner="TURKEY",  occupied="TURKEY",  kind="A")
        self["Den"] = Territory()
        self["Edi"] = Territory(owner="ENGLAND", occupied="ENGLAND", kind="F")
        self["Fin"] = Territory()
        self["Gal"] = Territory()
        self["Gas"] = Territory()
        self["Gre"] = Territory()
        self["Hol"] = Territory()
        self["Kie"] = Territory(owner="GERMANY", occupied="GERMANY", kind="F")
        self["Lon"] = Territory(owner="ENGLAND", occupied="ENGLAND", kind="F")
        self["Lvn"] = Territory()
        self["Lvp"] = Territory(owner="ENGLAND", occupied="ENGLAND", kind="A")
        self["Mar"] = Territory(owner="FRANCE",  occupied="FRANCE",  kind="A")
        self["Mos"] = Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="A")
        self["Mun"] = Territory(owner="GERMANY", occupied="GERMANY", kind="A")
        self["NAf"] = Territory()
        self["Nap"] = Territory(owner="ITALY",   occupied="ITALY",   kind="F")
        self["Nwy"] = Territory()
        self["Par"] = Territory(owner="FRANCE",  occupied="FRANCE",  kind="A")
        self["Pic"] = Territory()
        self["Pie"] = Territory()
        self["Por"] = Territory()
        self["Pru"] = Territory()
        self["Rom"] = Territory(owner="ITALY",   occupied="ITALY",   kind="A")
        self["Ruh"] = Territory()
        self["Rum"] = Territory()
        self["Ser"] = Territory()
        self["Sev"] = Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="F")
        self["Sil"] = Territory()
        self["Smy"] = Territory(owner="TURKEY",  occupied="TURKEY",  kind="A")
        self["Spa"] = Territory()
        self["StP"] = Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="F",  coast="(SC)")
        self["Swe"] = Territory()
        self["Syr"] = Territory()
        self["Tri"] = Territory(owner="AUSTRIA", occupied="AUSTRIA", kind="F")
        self["Tun"] = Territory()
        self["Tus"] = Territory()
        self["Tyr"] = Territory()
        self["Ukr"] = Territory()
        self["Ven"] = Territory(owner="ITALY",   occupied="ITALY",   kind="A")
        self["Vie"] = Territory(owner="AUSTRIA", occupied="AUSTRIA", kind="A")
        self["Wal"] = Territory()
        self["War"] = Territory(owner="RUSSIA",  occupied="RUSSIA",  kind="A")
        self["Yor"] = Territory()
        self["AEG"] = Territory()
        self["ADR"] = Territory()
        self["BAL"] = Territory()
        self["BAR"] = Territory()
        self["BLA"] = Territory()
        self["BOT"] = Territory()
        self["EAS"] = Territory()
        self["ENG"] = Territory()
        self["HEL"] = Territory()
        self["ION"] = Territory()
        self["IRI"] = Territory()
        self["LYO"] = Territory()
        self["MAO"] = Territory()
        self["NAO"] = Territory()
        self["NTH"] = Territory()
        self["NWG"] = Territory()
        self["SKA"] = Territory()
        self["TYS"] = Territory()
        self["WES"] = Territory()

    def occupied(self, nations=nations):
        if isinstance(nations, str):
            nations = {nations}

        return {t for t in territories if self[t].occupied in nations}

    def owned(self, nations=nations):
        if isinstance(nations, str):
            nations = {nations}

        return {t for t in supp_centers if self[t].owner in nations}

    def reachable(self, t):
        assert self[t].occupied

        if self[t].kind == "A":
            return land_graph.neighbors({t})

        if t in split_coasts:
            t += self[t].coast

        return {strip_coast(x) for x in sea_graph.neighbors({t})}

    def reachable_via_c(self, t, excluded={}):
        assert t in coast and self[t].occupied and self[t].kind == "A"

        to_check = full_graph.neighbors({t}) & offshore
        checked = set()
        ret = set()

        while to_check:
            t1 = to_check.pop()
            checked.add(t1)

            if not self[t1].occupied or t1 in excluded:
                continue

            for t2 in sea_graph.neighbors({t1}):
                t2 = strip_coast(t2)

                if t2 in coast:
                    ret.add(t2)

                elif t2 not in checked:
                    to_check.add(t2)

        ret.discard(t)

        return ret

    def contiguous_fleets(self, ts):
        assert all(t in offshore for t in ts)

        nations = {self[t].occupied for t in ts if self[t].occupied}

        to_check = sea_graph.neighbors(ts)
        checked = set()
        ret = copy(ts)

        while to_check:
            t = to_check.pop()

            checked.add(t)

            if (t in offshore
                    and self[t].occupied
                    and self[t].occupied not in nations):

                ret.add(t)

                to_check |= sea_graph.neighbors({t}) - checked

        return ret
