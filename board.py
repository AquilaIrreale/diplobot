
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


import re

from itertools import chain
from collections import UserString
from functools import total_ordering

from graph import Graph
from utils import StrEnum, casefold_mapping
from database import StringEnumColumn, UserStringColumn
from enum import auto


RE_TERR_COAST = re.compile(r"(?P<terr>\w+)\s*(?:\((?P<coast>\w+)\))?", re.I)

with open("assets/sea_graph") as f:
    sea_graph = Graph.from_file(f)

with open("assets/land_graph") as f:
    land_graph = Graph.from_file(f)

full_graph = Graph()
all_edges = chain(sea_graph.edges(), land_graph.edges())
for (v1, v2) in all_edges:
    t1 = RE_TERR_COAST.fullmatch(v1).group("terr")
    t2 = RE_TERR_COAST.fullmatch(v2).group("terr")
    full_graph.add_vertex(t1)
    full_graph.add_vertex(t2)
    full_graph.add_edge(t1, t2)
del all_edges


class UnitType(UserString):
    def __new__(cls, s):
        if type(s) is cls:
            return s
        else:
            return super().__new__(cls)

    def __init__(self, s):
        if s is self:
            return
        unit = s.strip().upper()
        if unit not in ("A", "F"):
            raise ValueError(f"{repr(s)} is not a valid unit type")
        super().__init__(unit)

    def __repr__(self):
        return f"UnitType({repr(str(self))})"

    def __hash__(self):
        return hash(str(self))


class UnitTypeColumn(UserStringColumn):
    cls = UnitType


class Coast(UserString):
    def __new__(cls, s):
        if type(s) is cls:
            return s
        else:
            return super().__new__(cls)

    def __init__(self, s):
        if s is self:
            return
        if s is None:
            s = ""
        us = s.strip().upper()
        if us not in ("NC", "SC", ""):
            raise ValueError(f"{repr(s)} is not a valid coast")
        super().__init__(us)

    def __repr__(self):
        return f"Coast({repr(str(self) or None)})"

    def __hash__(self):
        return hash(str(self))


class CoastColumn(UserStringColumn):
    cls = Coast


@total_ordering
class Terr(UserString):
    _names = casefold_mapping(full_graph.vertices())

    def __new__(cls, s):
        if type(s) is cls:
            return s
        else:
            return super().__new__(cls)

    def __init__(self, s):
        if s is self:
            return
        cs = s.strip().casefold()
        try:
            super().__init__(self._names[cs])
        except KeyError as e:
            raise ValueError(f"{repr(s)} is not a valid territory") from e

    def __repr__(self):
        return f"Terr({repr(str(self))})"

    def __eq__(self, other):
        return str(self).casefold() == str(other).casefold()

    def __lt__(self, other):
        return str(self).casefold() < str(other).casefold()

    def __hash__(self):
        return hash(str(self))


class TerrColumn(UserStringColumn):
    cls = Terr


split_coasts = set()
for v in sea_graph.vertices():
    m = RE_TERR_COAST.fullmatch(v)
    if m.group("coast"):
        split_coasts.add(Terr(m.group("terr")))


@total_ordering
class TerrCoast(UserString):
    def __init__(self, terr, coast=None):
        if coast is None:
            s = terr.strip()
            m = RE_TERR_COAST.fullmatch(s)
            if not m:
                raise ValueError(f"{repr(s)} is not a valid territory with coast")
            terr = m.group("terr")
            coast = m.group("coast")
        self.terr = Terr(terr)
        self.coast = Coast(coast)
        if self.coast and self.terr not in split_coasts:
            raise ValueError(
                f"{repr(str(coast))}: coast specified "
                f"for non split coast territory {repr(str(terr))}")

    def __repr__(self):
        return f"TerrCoast({repr(str(self.terr))}, {repr(str(self.coast))})"

    def __str__(self):
        return f"{str(self.terr)}({str(self.coast)})"

    def __eq__(self, other):
        return (self.terr, self.coast) == (other.terr, other.coast)

    def __lt__(self, other):
        return (self.terr, self.coast) < (other.terr, other.coast)

    def __hash__(self):
        return hash(str(self))


class TerrCoastColumn(UserStringColumn):
    cls = TerrCoast


@StrEnum.caseless
class Nation(StrEnum):
    AUSTRIA = auto()
    ENGLAND = auto()
    FRANCE  = auto()
    GERMANY = auto()
    ITALY   = auto()
    RUSSIA  = auto()
    TURKEY  = auto()

    @classmethod
    def parse(cls, s):
        try:
            return cls(s.strip().upper())
        except ValueError as e:
            raise ValueError(f"{repr(s)} is not a valid nation") from e


class NationColumn(StringEnumColumn):
    cls = Nation


#def strip_coast(t):
#    return t[:3]
#
#
#def get_coast(t):
#    return t[3:]
#
#
#offshore = {t for t in sea_graph.vertices() if strip_coast(t) not in land_graph.vertices()}
#coast = {strip_coast(t) for t in sea_graph.vertices() - offshore}
#
#offshore_graph = Graph({
#    t1: {t2 for t2 in t2s if t2 in offshore}
#    for t1, t2s in sea_graph.adj_dict.items()
#    if t1 in offshore
#})
#
#seas = tuple(offshore_graph.components())
#coasts = tuple(sea_graph.neighbors(sea) for sea in seas)
#
#split_coasts = {t for t in coast if tuple(map(strip_coast, sea_graph.vertices())).count(t) > 1}
#
#supp_centers = set()
#home_centers = {}
#
#with open("assets/supply_centers") as f:
#    nation = None
#
#    for line in f:
#        if not line.strip():
#            continue
#
#        try:
#            nation, rhs = tuple(map(str.strip, line.split(":")))
#
#        except ValueError as e:
#            if nation is None:
#                raise e
#
#            rhs = line
#
#        centers = set(filter(None, (t.strip() for t in rhs.split(" "))))
#        supp_centers |= centers
#
#        if nation:
#            try:
#                home_centers[nation].update(centers)
#
#            except KeyError:
#                home_centers[nation] = centers
#
#nations = sorted(n for n in home_centers)
#
#default_kind = {}
#default_coast = {}
#
#with open("assets/default_units") as f:
#    for line in f:
#        if not line.strip():
#            continue
#
#        words = tuple(filter(None, (s.strip() for s in line.split(" "))))
#
#        try:
#            t, kind, coast = words
#
#        except ValueError:
#            t, kind = words
#            coast = None
#
#        default_kind[t] = kind
#        default_coast[t] = coast
#
#
#def infer_kind(t):
#    return ("F" if t in offshore else
#            "A" if t not in coast else None)
#
#
#class Territory:
#    def __init__(self, owner=None, occupied=None, kind=None, coast=None):
#        self.owner = owner
#        self.occupied = occupied
#        self.kind = kind
#        self.coast = coast
#
#    def __repr__(self):
#        return "Territory(owner={}, occupied={}, kind={}, coast={})".format(
#            repr(self.owner), repr(self.occupied), repr(self.kind), repr(self.coast))
#
#
#class Board(dict):
#    def __init__(self):
#        super().__init__(self)
#
#        for t in territories:
#            for n in nations:
#                if t in home_centers[n]:
#                    self[t] = Territory(owner=n,
#                                        occupied=n,
#                                        kind=default_kind[t],
#                                        coast=default_coast[t])
#                    break
#
#            else:
#                self[t] = Territory()
#
#    def occupied(self, nations=nations):
#        if isinstance(nations, str):
#            nations = {nations}
#
#        return {t for t in territories if self[t].occupied in nations}
#
#    def owned(self, nations=nations):
#        if isinstance(nations, str):
#            nations = {nations}
#
#        return {t for t in supp_centers if self[t].owner in nations}
#
#    def valid_dests(self, t):
#        if not self[t].occupied:
#            return set()
#
#        if self[t].kind == "A":
#            return land_graph.neighbors(t)
#
#        if t in split_coasts:
#            assert self[t].coast in {"(NC)", "(SC)"}
#            t += self[t].coast
#
#        return {strip_coast(x) for x in sea_graph.neighbors(t)}
#
#    def valid_dests_via_c(self, t, excluded={}):
#        if (t not in coast
#                or not self[t].occupied
#                or self[t].kind != "A"):
#
#            return set()
#
#        to_check = full_graph.neighbors(t) & offshore
#        checked = set()
#        ret = set()
#
#        while to_check:
#            t1 = to_check.pop()
#            checked.add(t1)
#
#            if not self[t1].occupied or t1 in excluded:
#                continue
#
#            for t2 in sea_graph.neighbors(t1):
#                t2 = strip_coast(t2)
#
#                if t2 in coast:
#                    ret.add(t2)
#
#                elif t2 not in checked:
#                    to_check.add(t2)
#
#        ret.discard(t)
#
#        return ret
#
#    def contiguous_fleets(self, ts):
#        assert all(t in offshore for t in ts)
#
#        nations = {self[t].occupied for t in ts if self[t].occupied}
#
#        to_check = sea_graph.neighbors(ts)
#        checked = set()
#        ret = set(ts)
#
#        while to_check:
#            t = to_check.pop()
#
#            checked.add(t)
#
#            if (t in offshore
#                    and self[t].occupied
#                    and self[t].occupied not in nations):
#
#                ret.add(t)
#
#                to_check |= sea_graph.neighbors(t) - checked
#
#        return ret
#
#    def needs_via_c(self, t1, t2):
#        assert self[t1].occupied
#
#        ts = {t1, t2}
#
#        if (not ts.issubset(coast)
#                or self[t1].kind != "F"
#                or t2 not in self.valid_dests(t1)):
#
#            return False
#
#        for t3 in full_graph.shared_neighbors(ts):
#            if (t3 in offshore
#                    and self[t3].occupied
#                    and self[t3].occupied != self[t1].occupied):
#
#                return True
#
#        return False
#
#    def needs_coast(self, t1, t2):
#        assert self[t1].occupied
#
#        return self[t1].kind == "F" and t2 in split_coasts
#
#    def infer_coast(self, t1, t2):
#        assert self[t1].occupied
#        assert self[t1].kind == "F"
#        assert t2 in split_coasts
#        assert t2 in self.valid_dests(t1)
#
#        neighs = sea_graph.neighbors(t1)
#
#        if ({t2 + "(NC)", t2 + "(SC)"}.issubset(neighs)):
#            return None
#
#        return next(get_coast(t) for t in neighs if strip_coast(t) == t2)
#
#
