#!/usr/bin/env python3

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

        else:
            raise KeyError
