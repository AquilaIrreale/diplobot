#!/usr/bin/env python3

  ########################################################################
  # insensitive_list.py - a simple case-insensitive list                 #
  #                                                                      #
  # Copyright (C) 2018 Simone Cimarelli a.k.a. AquilaIrreale             #
  #                                                                      #
  # To the extent possible under law, the author(s) have dedicated all   #
  # copyright and related and neighboring rights to this software to the #
  # public domain worldwide. This software is distributed without any    #
  # warranty. <http://creativecommons.org/publicdomain/zero/1.0/>        #
  ########################################################################

class InsensitiveList(list):
    def __init__(self, iterable):
        super().__init__(iterable)

    def __contains__(self, item):
        return item.upper() in (x.upper() for x in self)

    def match_case(self, item):
        item_upper = item.upper()

        for elem, upper in zip(self, (x.upper() for x in self)):
            if upper == item_upper:
                return elem

        raise KeyError
