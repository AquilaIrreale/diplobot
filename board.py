
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


sea_graph = load_graph("sea_graph")
land_graph = load_graph("land_graph")


def strip_coast(t):
    return t[:3]


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

with open("supply_centers") as f:
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

with open("default_units") as f:
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


def make_board():
    ret = {}

    for t in territories:
        for n in nations:
            if t in home_centers[n]:
                ret[t] = Territory(owner=n,
                                   occupied=n,
                                   kind=default_kind[t],
                                   coast=default_coast[t])
                break

        else:
            ret[t] = Territory()

    return ret


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
