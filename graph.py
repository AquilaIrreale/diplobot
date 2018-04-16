#!/usr/bin/env python3

class Graph:
    def __init__(self, graph_dict=None):
        if graph_dict is None:
            graph_dict = {}

        self.__graph_dict = graph_dict

    @property
    def dict(self):
        return self.__graph_dict

    def vertices(self):
        return list(self.__graph_dict.keys())

    def edges(self):
        return self.__generate_edges()

    def add_vertex(self, vertex):
        if vertex not in self.__graph_dict:
            self.__graph_dict[vertex] = []

    def add_edge(self, edge):
        edge = set(edge)
        (vertex1, vertex2) = tuple(edge)

        if vertex1 in self.__graph_dict:
            self.__graph_dict[vertex1].append[vertex2]
        else:
            self.__graph_dict[vertex1] = [vertex2]

    def __generate_edges(self):
        edges = []
        for vertex in self.__graph_dict:
            for neighbour in self.__graph_dict[vertex]:
                if {neighbour, vertex} not in edges:
                    edges.append({vertex, neighbour})
        return edges

    def __str__(self):
        res = "Vertices: "

        for k in self.__graph_dict:
            res +=str(k)+ " "

        res += "\nEdges: "

        for edge in self.__generate_edges():
            res += str(edge) + " "

        return res
