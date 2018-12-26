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


import math
import heapq


class Graph:
    def __init__(self, graph_dict=None):
        if graph_dict is None:
            graph_dict = {}

        self._graph_dict = graph_dict

    @property
    def dict(self):
        return self._graph_dict

    def vertices(self):
        return set(self._graph_dict.keys())

    def edges(self):
        edges = set()

        for v in self._graph_dict:
            for neigh in self._graph_dict[v]:
                s = frozenset((neigh, v))
                if s not in edges:
                    edges.add(s)

        return edges

    def add_vertex(self, v):
        if v not in self._graph_dict:
            self._graph_dict[v] = set()

    def add_edge(self, edge):
        edge = set(edge)
        (v1, v2) = tuple(edge)
        self._half_add_edge(v1, v2)
        self._half_add_edge(v2, v1)

    def _half_add_edge(self, v1, v2):
        if v1 in self._graph_dict:
            self._graph_dict[v1].add(v2)

        else:
            self._graph_dict[v1] = {v2}

    def neighbors(self, vs):
        ret = set()

        for v in vs:
            ret |= self._graph_dict[v]

        return ret - set(vs)

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
            ", ".join(sorted(self._graph_dict.keys())),
            ", ".join(sorted("({}, {})".format(*sorted(e)) for e in self.edges()))
        )
