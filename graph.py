#!/usr/bin/env python3

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
            self._graph_dict[v1].add[v2]

        else:
            self._graph_dict[v1] = {v2}



    def __str__(self):
        res = "Vertices: "

        for k in self._graph_dict:
            res += str(k) + " "

        res += "\nEdges: "

        for edge in self.edges():
            res += str(edge) + " "

        return res
