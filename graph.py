#!/usr/bin/env python3

  ########################################################################
  # graph.py - a simple graph based on adjacency-lists                   #
  #                                                                      #
  # Copyright (C) 2018 Simone Cimarelli a.k.a. AquilaIrreale             #
  #                                                                      #
  # To the extent possible under law, the author(s) have dedicated all   #
  # copyright and related and neighboring rights to this software to the #
  # public domain worldwide. This software is distributed without any    #
  # warranty. <http://creativecommons.org/publicdomain/zero/1.0/>        #
  ########################################################################

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

    def __str__(self):
        res = "Vertices: "

        for k in self._graph_dict:
            res += str(k) + " "

        res += "\nEdges: "

        for edge in self.edges():
            res += str(edge) + " "

        return res
