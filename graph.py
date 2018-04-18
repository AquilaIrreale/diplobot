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
        edges = {}

        for v in self._graph_dict:
            for neigh in self._graph_dict[v]:
                if {neigh, v} not in edges:
                    edges.add({v, neigh})

        return edges

    def add_vertex(self, v):
        if v not in self._graph_dict:
            self._graph_dict[v] = set()

    def add_edge(self, edge):
        edge = set(edge)
        (v1, v2) = tuple(edge)

        if v1 in self._graph_dict:
            self._graph_dict[v1].add(v2)

        else:
            self._graph_dict[v1] = {v2}

    def neighbors(self, vs):
        ret = set()

        for v in vs:
            ret |= self._graph_dict[v]

        return ret - set(vs)

    def __str__(self):
        res = "Vertices: "

        for k in self._graph_dict:
            res += str(k) + " "

        res += "\nEdges: "

        for edge in self.edges():
            res += str(edge) + " "

        return res
