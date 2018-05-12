#!/usr/bin/env python3

  ############################################################################
  # diplobot.py - play Diplomacy through Telegram                            #
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


import re

from copy import copy, deepcopy
from operator import attrgetter, itemgetter
from itertools import chain
from functools import total_ordering


@total_ordering
class Order:
    def __init__(self):
        self.kind = None
        self.terr = None
        self.orig = None
        self.targ = None
        self.coast = None
        self.via_c = None

    def __str__(self):
        coast = "{}".format(self.coast) if self.coast else ""
        via_c = " C" if self.via_c else ""

        if self.kind == "HOLD":
            return "{} H".format(self.terr)

        if self.kind == "MOVE":
            return "{}-{}{}{}".format(self.terr, self.targ, coast, via_c)

        if self.kind == "SUPH":
            return "{} S {}".format(self.terr, self.targ)

        if self.kind == "SUPM":
            return "{} S {}-{}".format(self.terr, self.orig, self.targ)

        if self.kind == "CONV":
            return "{} C {}-{}".format(self.terr, self.orig, self.targ)

        return "Invalid order"

    def key(self):
        if self.kind == "HOLD":
            ret = (0, self.terr,)
        elif self.kind == "SUPH":
            ret = (0, self.targ, self.terr)
        elif self.kind == "MOVE":
            ret = (1, self.terr, self.targ)
        elif self.kind == "SUPM":
            ret = (1, self.orig, self.targ, 0, self.terr)
        elif self.kind == "CONV":
            ret = (1, self.orig, self.targ, 1, self.terr)
        else:
            raise ValueError

        return tuple(x.casefold() if isinstance(x, str) else x for x in ret)

    def __lt__(self, other):
        return self.key() < other.key()

    def __eq__(self, other):
        return self.key() == other.key()


class BuilderError(Exception):
    def __init__(self, message):
        super().__init__(self)
        self.message = message


class OrderBuilder:
    def __init__(self, board, nation):
        self.board = board
        self.orders = set()
        self.nation = nation
        self.building = None
        self.terrs = set()
        self.terr_complete = False
        self.terr_remove = False
        self.more = False

    def __bool__(self):
        return bool(self.orders)

    def new(self):
        self.building = Order()
        self.terrs = set()
        self.terr_complete = False
        self.terr_remove = False
        self.more = False

    @property
    def terr(self):
        try:
            return next(iter(self.terrs))
        except StopIteration:
            return None

    def next_to_fill(self):
        if self.building.kind is None:
            return "KIND"

        if not self.terr_complete:
            return "TERR"

        if self.building.kind == "HOLD":
            return "DONE"

        if self.building.orig is None and self.building.kind in {"SUPM", "CONV"}:
            return "ORIG"

        if self.building.targ is None:
            return "TARG"

        if self.building.kind == "MOVE":
            if self.building.via_c is None and self.needs_via_c():
                return "VIAC"
            elif self.building.coast is None and not self.auto_coast():
                return "COAST"

        return "DONE"

    kinds = {
        "H":               "HOLD",
        "HOL":             "HOLD",
        "HOLD":            "HOLD",
        "M":               "MOVE",
        "MOV":             "MOVE",
        "MOVE":            "MOVE",
        "ATTACK":          "MOVE",
        "MOVE (ATTACK)":   "MOVE",
        "SH":              "SUPH",
        "SUPPORT HOLD":    "SUPH",
        "SUPPORT TO HOLD": "SUPH",
        "SUPPORT A HOLD":  "SUPH",
        "SM":              "SUPM",
        "SUPPORT MOVE":    "SUPM",
        "SUPPORT TO MOVE": "SUPM",
        "SUPPORT A MOVE":  "SUPM",
        "C":               "CONV",
        "CON":             "CONV",
        "CONVOY":          "CONV"
    }

    kind_codes = set(kinds.values())

    def register_kind(self, s):
        try:
            self.building.kind = self.kinds[s]
        except KeyError:
            pass
        else:
            return

        if s in self.kind_codes:
            self.building.kind = s
        else:
            raise ValueError

    def register_terr_list(self, s):
        if s == "DONE":
            if not self.terrs:
                raise BuilderError("You must specify at least one territory")

            self.terr_complete = True
            self.more = False
            return

        if s == "REMOVE":
            if not self.terrs:
                raise ValueError

            self.terr_remove = True
            return

        if s == "ADD":
            self.terr_remove = False
            self.more = False
            return

        try:
            t = terr_names.match_case(s)
        except KeyError:
            raise ValueError

        if self.terr_remove:
            try:
                self.terrs.remove(t)
            except KeyError:
                raise ValueError

            if not self.terrs:
                self.terr_remove = False
        else:
            self.validate_terr(t)

            self.terrs.add(t)

            if self.building.kind not in {"SUPH", "SUPM", "CONV"}:
                self.terr_complete = True

    def register_orig(self, s):
        try:
            t = terr_names.match_case(s)
        except KeyError:
            raise ValueError

        self.validate_orig(t)

        self.building.orig = t
        self.more = False

    def register_targ(self, s):
        try:
            t = terr_names.match_case(s)
        except KeyError:
            raise ValueError

        self.validate_targ(t)

        self.building.targ = t
        self.more = False

    def register_viac(self, s):
        if s in {"YES", "Y"}:
            self.building.via_c = True
        elif s in {"NO", "N"}:
            self.building.via_c = False
        else:
            raise ValueError

    def register_coast(self, s):
        if s in {"N", "NC", "(NC)", "NORTH", "NORTH COAST"}:
            self.building.coast = "(NC)"
        elif s in {"S", "SC", "(SC)", "SOUTH", "SOUTH COAST"}:
            self.building.coast = "(SC)"
        else:
            raise ValueError

    actions = {
        "KIND":  lambda self, s: self.register_kind(s),
        "TERR":  lambda self, s: self.register_terr_list(s),
        "ORIG":  lambda self, s: self.register_orig(s),
        "TARG":  lambda self, s: self.register_targ(s),
        "VIAC":  lambda self, s: self.register_viac(s),
        "COAST": lambda self, s: self.register_coast(s)
    }

    back_attrs = ["via_c", "coast", "targ", "orig", "terrs", "kind"]

    def back(self):
        for attr in self.back_attrs:
            if attr != "terrs":
                if getattr(self.building, attr) is not None:
                    setattr(self.building, attr, None)
                    break

            elif self.terr_complete:
                break

        else:
            raise IndexError

        if attr in ["terrs", "kind"]:
            self.terrs = set()
            self.terr_complete = False

        self.more = False
        self.terr_remove = False

    def push(self, s):
        s = s.strip().upper()

        ntf = self.next_to_fill()

        if s == "BACK":
            self.back()

        elif s in {"MORE", "MORE..."}:
            self.more = not self.more

        elif ntf == "DONE":
            raise IndexError

        else:
            self.actions[ntf](self, s)

        return self.next_to_fill()

    def validate_terr(self, t):
        if not self.board[t].occupied:
            raise BuilderError("There's no unit in " + t)

        if self.board[t].occupied != self.nation:
            raise BuilderError("You can't order someone else's unit")

        if self.building.kind == "CONV":
            if self.board[t].kind != "F":
                raise BuilderError("Only fleets can convoy")

            elif t not in offshore:
                raise BuilderError("A fleet needs to be in open sea to convoy")


        for o in self.orders:
            if o.terr == t:
                raise BuilderError("There's already another order for {} ({})".format(t, o))

    def validate_orig(self, t):
        if t in self.terrs:
            raise BuilderError("{} is already part of the order".format(t))

    def validate_targ(self, t):
        t2 = self.terr if self.building.kind == "MOVE" else self.building.orig

        if t == t2:
            raise BuilderError("Can't move onto itself")

    def ordered(self):
        return {o.terr for o in self.orders}

    def unordered(self):
        return occupied(self.board, self.nation) - self.ordered()

    def get_terrs_hint(self):
        if self.terr_remove:
            return self.terrs

        available = self.unordered() - self.terrs

        if self.building.kind == "CONV":
            return available & offshore
        else:
            return available

    def get_origs_hint(self):
        ret = set()

        if self.building.kind == "SUPM":
            common_neighbors = copy(territories)

            for t in self.terrs:
                common_neighbors &= reachables(t, self.board)

            for t in territories:
                if (not reachables(t, self.board).isdisjoint(common_neighbors)
                        or not reachables_via_c(t, self.board, self.terrs)
                            .isdisjoint(common_neighbors)):

                    ret.add(t)

            ret -= self.terrs

        elif self.building.kind == "CONV":
            for t in sea_graph.neighbors(contiguous_fleets(self.terrs, self.board)):
                if self.board[t].occupied and self.board[t].kind == "A":
                    ret.add(t)

        return ret

    def get_targs_hint(self):
        if self.building.kind == "MOVE":
            return (reachables(self.terr, self.board)
                    | reachables_via_c(self.building.orig, self.board))

        if self.building.kind == "SUPH":
            return reachables(self.terr, self.board)

        elif self.building.kind == "SUPM":
            common_neighbors = copy(territories)

            for t in self.terrs:
                common_neighbors &= reachables(t, self.board)

            return (
                common_neighbors & (
                    reachables(self.building.orig, self.board)
                    | reachables_via_c(
                        self.building.orig, self.board, self.terrs)))

        elif self.building.kind == "CONV":
            return reachables_via_c(self.building.orig, self.board)


    hints = {
        "TERR": lambda self: self.get_terrs_hint(),
        "ORIG": lambda self: self.get_origs_hint(),
        "TARG": lambda self: self.get_targs_hint()
    }

    @staticmethod
    def get_kind_keyboard():
        return RKM([
            ["Hold"],
            ["Move (attack)"],
            ["Support to Hold"],
            ["Support to Move"],
            ["Convoy"],
            ["Back"]
        ])

    @staticmethod
    def get_coasts_keyboard():
        return RKM([
            ["North", "South"],
            ["Back"]
        ])

    @staticmethod
    def get_yesno_keyboard():
        return RKM([
            ["Yes", "No"],
            ["Back"]
        ])

    basic_keyboards = {
        "KIND":  lambda self: self.get_kind_keyboard(),
        "COAST": lambda self: self.get_coasts_keyboard(),
        "VIAC":  lambda self: self.get_yesno_keyboard()
    }

    def get_keyboard(self):
        ntf = self.next_to_fill()

        try:
            return self.basic_keyboards[ntf](self)
        except KeyError:
            pass

        try:
            hint = self.hints[ntf](self)
        except KeyError:
            return None

        if self.more:
            hint = territories - hint

        keyboard = make_grid(sorted(hint, key=str.casefold))

        keyboard.append(["More..."])

        if ntf == "TERR" and self.terrs:
            if not self.terr_remove:
                keyboard.append(["Remove"])
            else:
                keyboard.append(["Add"])

            keyboard.append(["Done"])

        keyboard.append(["Back"])

        return RKM(keyboard)
