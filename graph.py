
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


import math
import heapq
from itertools import chain


class Graph:
    def __init__(self, adj_dict={}):
        if adj_dict is None:
            adj_dict = {}
        self.adj_dict = adj_dict

    @classmethod
    def from_file(cls, file):
        adj_dict = {}
        for line in file:
            line = line.strip()
            if not line:
                continue
            t1, t2s = line.split(":", maxsplit=1)
            t1 = t1.strip()
            adj_dict[t1] = set(t2s.split())
        return cls(adj_dict)

    def vertices(self):
        return set(self.adj_dict.keys())

    def edges(self):
        edges = set()

        for v in self.adj_dict:
            for neigh in self.adj_dict[v]:
                edges.add(frozenset((neigh, v)))

        return edges

    def add_vertex(self, v):
        self.adj_dict.setdefault(v, set())

    def add_edge(self, v1, v2):
        for v in v1, v2:
            if v not in self.adj_dict:
                raise ValueError(f"{repr(v)} is not a vertex of this graph")
        self._add_edge(v1, v2)
        self._add_edge(v2, v1)

    def _add_edge(self, v1, v2):
        self.adj_dict[v1].add(v2)

    def neighbors(self, vs):
        if isinstance(vs, str):
            vs = (vs,)

        ret = set()

        for v in vs:
            ret |= self.adj_dict[v]

        return ret - set(vs)

    def shared_neighbors(self, vs):
        if isinstance(vs, str):
            vs = (vs,)

        ret = set(self.vertices())

        for v in vs:
            ret &= self.neighbors((v,))

        return ret

    def distances(self, v):
        distances = {v: math.inf for v in self.vertices()}
        distances[v] = 0
        queue = [(0, v)]

        while queue:
            curdist, cur = heapq.heappop(queue)

            changed = set()

            for n in self.neighbors((cur,)):
                if curdist + 1 < distances[n]:
                    distances[n] = curdist + 1
                    changed.add(n)

            for i, (p, v) in enumerate(queue):
                if v in changed:
                    queue[i] = (curdist + 1, v)
                    changed.discard(v)

                    if not changed:
                        break

            for v in changed:
                queue.append((curdist + 1, v))

            heapq.heapify(queue)

        return distances

    def components(self):
        vertices = self.vertices()

        while vertices:
            component = {vertices.pop()}
            neighs = self.neighbors(component)

            while neighs:
                vertices -= neighs
                component |= neighs
                neighs = self.neighbors(component)

            yield component

    def __str__(self):
        return "Vertices: {}\nEdges: {}".format(
            ", ".join(sorted(self.adj_dict.keys())),
            ", ".join(sorted("({}, {})".format(*sorted(e)) for e in self.edges()))
        )
