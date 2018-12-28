
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


from copy import copy
from itertools import chain

from graph import Graph
from insensitive_list import InsensitiveList


def load_graph(filename):

    graph_dict = {}

    with open(filename) as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            t1, t2s = tuple(line.split(":"))
            t1 = t1.strip()

            graph_dict[t1] = set(filter(None, (s.strip() for s in t2s.split(" "))))

    return Graph(graph_dict)


sea_graph = load_graph("assets/sea_graph")
land_graph = load_graph("assets/land_graph")


def strip_coast(t):
    return t[:3]


def get_coast(t):
    return t[3:]


full_graph = Graph()

for t1, t2 in chain(sea_graph.edges(), land_graph.edges()):
    full_graph.add_edge((strip_coast(t1), strip_coast(t2)))

territories = {
    strip_coast(t) for t in chain(land_graph.vertices(), sea_graph.vertices())
}

terr_names = InsensitiveList(sorted({strip_coast(t) for t in territories}, key=str.upper))

offshore = {t for t in sea_graph.vertices() if strip_coast(t) not in land_graph.vertices()}
coast = {strip_coast(t) for t in sea_graph.vertices() - offshore}

offshore_graph = Graph({
    t1: {t2 for t2 in t2s if t2 in offshore}
    for t1, t2s in sea_graph.dict.items()
    if t1 in offshore
})

seas = tuple(offshore_graph.components())
coasts = tuple(sea_graph.neighbors(sea) for sea in seas)

split_coasts = {t for t in coast if tuple(map(strip_coast, sea_graph.vertices())).count(t) > 1}

supp_centers = set()
home_centers = {}

with open("assets/supply_centers") as f:
    nation = None

    for line in f:
        if not line.strip():
            continue

        try:
            nation, rhs = tuple(map(str.strip, line.split(":")))

        except ValueError as e:
            if nation is None:
                raise e

            rhs = line

        centers = set(filter(None, (t.strip() for t in rhs.split(" "))))
        supp_centers |= centers

        if nation:
            try:
                home_centers[nation].update(centers)

            except KeyError:
                home_centers[nation] = centers

nations = sorted(n for n in home_centers)

default_kind = {}
default_coast = {}

with open("assets/default_units") as f:
    for line in f:
        if not line.strip():
            continue

        words = tuple(filter(None, (s.strip() for s in line.split(" "))))

        try:
            t, kind, coast = words

        except ValueError:
            t, kind = words
            coast = None

        default_kind[t] = kind
        default_coast[t] = coast


def infer_kind(t):
    return ("F" if t in offshore else
            "A" if t not in coast else None)


class Territory:
    def __init__(self, owner=None, occupied=None, kind=None, coast=None):
        self.owner = owner
        self.occupied = occupied
        self.kind = kind
        self.coast = coast

    def __repr__(self):
        return "Territory(owner={}, occupied={}, kind={}, coast={})".format(
            self.owner, self.occupied, self.kind, self.coast)


class Board(dict):
    def __init__(self):
        super().__init__(self)

        for t in territories:
            for n in nations:
                if t in home_centers[n]:
                    self[t] = Territory(owner=n,
                                        occupied=n,
                                        kind=default_kind[t],
                                        coast=default_coast[t])
                    break

            else:
                self[t] = Territory()

    def occupied(self, nations=nations):
        if isinstance(nations, str):
            nations = {nations}

        return {t for t in territories if self[t].occupied in nations}

    def owned(self, nations=nations):
        if isinstance(nations, str):
            nations = {nations}

        return {t for t in supp_centers if self[t].owner in nations}

    def valid_dests(self, t):
        if not self[t].occupied:
            return set()

        if self[t].kind == "A":
            return land_graph.neighbors(t)

        if t in split_coasts:
            assert self[t].coast in {"(NC)", "(SC)"}
            t += self[t].coast

        return {strip_coast(x) for x in sea_graph.neighbors(t)}

    def valid_dests_via_c(self, t, excluded={}):
        if (t not in coast
                or not self[t].occupied
                or self[t].kind != "A"):

            return set()

        to_check = full_graph.neighbors(t) & offshore
        checked = set()
        ret = set()

        while to_check:
            t1 = to_check.pop()
            checked.add(t1)

            if not self[t1].occupied or t1 in excluded:
                continue

            for t2 in sea_graph.neighbors(t1):
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
        ret = set(ts)

        while to_check:
            t = to_check.pop()

            checked.add(t)

            if (t in offshore
                    and self[t].occupied
                    and self[t].occupied not in nations):

                ret.add(t)

                to_check |= sea_graph.neighbors(t) - checked

        return ret

    def needs_via_c(self, t1, t2):
        assert self[t1].occupied

        ts = {t1, t2}

        if (not ts.issubset(coast)
                or self[t1].kind != "F"
                or t2 not in self.valid_dests(t1)):

            return False

        for t3 in full_graph.shared_neighbors(ts):
            if (t3 in offshore
                    and self[t3].occupied
                    and self[t3].occupied != self[t1].occupied):

                return True

        return False

    def needs_coast(self, t1, t2):
        assert self[t1].occupied

        return self[t1].kind == "F" and t2 in split_coasts

    def infer_coast(self, t1, t2):
        assert self[t1].occupied
        assert self[t1].kind == "F"
        assert t2 in split_coasts
        assert t2 in self.valid_dests(t1)

        neighs = sea_graph.neighbors(t1)

        if ({t2 + "(NC)", t2 + "(SC)"}.issubset(neighs)):
            return None

        return next(get_coast(t) for t in neighs if strip_coast(t) == t2)
