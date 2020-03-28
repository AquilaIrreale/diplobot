
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


import re
from functools import total_ordering

from board import Unit, Terr, TerrCoast


class OrderParseError(Exception):
    pass


@total_ordering
class Order:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError

    def __repr__(self):
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

    def to_cdippy(self):
        raise NotImplementedError

    def _key(self):
        raise NotImplementedError

    def __lt__(self, other):
        if not isinstance(other, Order):
            raise TypeError
        return self._key() < other._key()

    def __eq__(self, other):
        if not isinstance(other, Order):
            raise TypeError
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    @classmethod
    def parse(cls, s):
        if cls is not Order:
            raise NotImplementedError

        for OrdType in cls.__subclasses__():
            try:
                return OrdType.parse(s)
            except OrderParseError:
                pass
        else:
            raise ValueError(
                f"{repr(s)} does not look like an order")


# Order RE patterns
RE_UNIT = r"(?P<unit>\w+)\s+"
RE_TERR = r"(?P<terr>\w+)"
RE_ORIG = r"(?P<orig>\w+)"
RE_TARG = r"(?P<targ>\w+)"
RE_COAS = r"(?:\s*\((?P<coast>\w+)\))?"
RE_HOLD = r"\s+H"
RE_SUPP = r"\s+S\s+"
RE_CONV = r"\s+C\s+"
RE_MOVE = r"\s*-\s*"
RE_VIAC = r"(?P<viac>\s+C)?"


def re_build(*args):
    pattern = "".join(args)
    return re.compile(pattern, re.I)


class HoldOrder(Order):
    def __init__(self, unit, terr):
        self.unit = Unit(unit)
        self.terr = Terr(terr)

    def __repr__(self):
        return (
            f"HoldOrder("
            f"{repr(self.unit)}, "
            f"{repr(self.terr)})")

    def __str__(self):
        return f"{self.unit} {self.terr} H"

    def to_cdippy(self):
        raise NotImplementedError #TODO

    def _key(self):
        return 0, self.terr

    RE = re_build(
        RE_UNIT,
        RE_TERR,
        RE_HOLD)

    @classmethod
    def parse(cls, s):
        s = s.strip()
        m = cls.RE.fullmatch(s)
        if not m:
            raise OrderParseError(
                f"{repr(s)} does not match a hold order")
        return cls(
            m.group("unit"),
            m.group("terr"))


class SupHoldOrder(Order):
    def __init__(self, unit, terr, targ):
        self.unit = Unit(unit)
        self.terr = Terr(terr)
        self.targ = Terr(targ)

    def __repr__(self):
        return (
            f"SupHoldOrder("
            f"{repr(self.unit)}, "
            f"{repr(self.terr)}, "
            f"{repr(self.targ)})")

    def __str__(self):
        return (
            f"{self.unit} {self.terr} "
            f"S {self.targ}")

    def to_cdippy(self):
        raise NotImplementedError #TODO

    def _key(self):
        return 0, self.targ, self.terr

    RE = re_build(
        RE_UNIT,
        RE_TERR,
        RE_SUPP,
        RE_TARG)

    @classmethod
    def parse(cls, s):
        s = s.strip()
        m = cls.RE.fullmatch(s)
        if not m:
            raise OrderParseError(
                f"{repr(s)} does not match a support to hold order")
        return cls(
            m.group("unit"),
            m.group("terr"),
            m.group("targ"))


class MoveOrder(Order):
    def __init__(self, unit, terr, targ, coast=None, viac=False):
        self.unit = Unit(unit)
        self.terr = Terr(terr)
        self.targ = TerrCoast(targ, coast)
        self.viac = bool(viac)

    def __repr__(self):
        return (
            f"MoveOrder("
            f"{repr(self.unit)}, "
            f"{repr(self.terr)}, "
            f"{repr(self.targ.terr)}, "
            f"{repr(self.targ.coast)}, "
            f"viac={self.viac})")

    def __str__(self):
        return (
            f"{self.unit} {self.terr}-{self.targ}"
            + " C" if self.viac else "")

    def to_cdippy(self):
        raise NotImplementedError #TODO

    def _key(self):
        return 1, self.terr, self.targ.terr

    RE = re_build(
        RE_UNIT,
        RE_TERR,
        RE_MOVE,
        RE_TARG,
        RE_COAS,
        RE_VIAC)

    @classmethod
    def parse(cls, s):
        s = s.strip()
        m = cls.RE.fullmatch(s)
        if not m:
            raise OrderParseError(
                f"{repr(s)} does not match a move order")
        return cls(
            m.group("unit"),
            m.group("terr"),
            m.group("targ"),
            m.group("coast"),
            m.group("viac"))


class SupMoveOrder(Order):
    def __init__(self, unit, terr, orig, targ):
        self.unit = Unit(unit)
        self.terr = Terr(terr)
        self.orig = Terr(orig)
        self.targ = Terr(targ)

    def __repr__(self):
        return (
            f"SupMoveOrder("
            f"{repr(self.unit)}, "
            f"{repr(self.terr)}, "
            f"{repr(self.orig)}, "
            f"{repr(self.targ)})")

    def __str__(self):
        return (
            f"{self.unit} {self.terr} "
            f"S {self.orig}-{self.targ}")

    def to_cdippy(self):
        raise NotImplementedError #TODO

    def _key(self):
        return 1, self.orig, self.targ, 0, self.terr

    RE = re_build(
        RE_UNIT,
        RE_TERR,
        RE_SUPP,
        RE_ORIG,
        RE_MOVE,
        RE_TARG)

    @classmethod
    def parse(cls, s):
        s = s.strip()
        m = cls.RE.fullmatch(s)
        if not m:
            raise OrderParseError(
                f"{repr(s)} does not match a support to move order")
        return cls(
            m.group("unit"),
            m.group("terr"),
            m.group("orig"),
            m.group("targ"))


class ConvOrder(Order):
    def __init__(self, unit, terr, orig, targ):
        self.unit = Unit(unit)
        self.terr = Terr(terr)
        self.orig = Terr(orig)
        self.targ = Terr(targ)

    def __repr__(self):
        return (
            f"ConvOrder("
            f"{repr(self.unit)}, "
            f"{repr(self.terr)}, "
            f"{repr(self.orig)},"
            f"{repr(self.targ)})")

    def __str__(self):
        return (
            f"{self.unit} {self.terr} "
            f"C {self.orig}-{self.targ}")

    def to_cdippy(self):
        raise NotImplementedError #TODO

    def _key(self):
        return 1, self.orig, self.targ, 1, self.terr

    RE = re_build(
        RE_UNIT,
        RE_TERR,
        RE_CONV,
        RE_ORIG,
        RE_MOVE,
        RE_TARG)

    @classmethod
    def parse(cls, s):
        s = s.strip()
        m = cls.RE.fullmatch(s)
        if not m:
            raise OrderParseError(
                f"{repr(s)} does not match a convoy order")
        return cls(
            m.group("unit"),
            m.group("terr"),
            m.group("orig"),
            m.group("targ"))


#class BuilderError(Exception):
#    def __init__(self, message):
#        super().__init__(self)
#        self.message = message
#
#
#class OrderBuilder:
#    def __init__(self, board, orders, nation=None):
#        self.board = board
#        self.orders = orders
#        self.nation = nation
#        self.building = None
#        self.terrs = set()
#        self.terr_complete = False
#        self.terr_remove = False
#        self.more = False
#
#    def __bool__(self):
#        return self.building is not None
#
#    def new(self):
#        self.building = Order()
#        self.terrs = set()
#        self.terr_complete = False
#        self.terr_remove = False
#        self.more = False
#
#    def pop(self):
#        ret = set()
#        for t in self.terrs:
#            o = copy(self.building)
#            o.terr = t
#            ret.add(o)
#
#        self.building = None
#        return ret
#
#    @property
#    def terr(self):
#        try:
#            return next(iter(self.terrs))
#        except StopIteration:
#            return None
#
#    def auto_coast(self):
#        if (self.board[self.terr].kind != "F"
#                or self.building.targ not in split_coasts):
#
#            return True
#
#        i = 0
#
#        for c in ("(NC)", "(SC)"):
#            try:
#                if self.terr in sea_graph.neighbors((self.building.targ + c,)):
#                    self.building.coast = c
#                    i += 1
#
#            except KeyError:
#                pass
#
#        if i != 1:
#            self.building.coast = None
#            return False
#
#        return True
#
#    def next_to_fill(self):
#        if self.building.kind is None:
#            return "KIND"
#
#        if not self.terr_complete:
#            return "TERR"
#
#        if self.building.kind == "HOLD":
#            return "DONE"
#
#        if self.building.orig is None and self.building.kind in {"SUPM", "CONV"}:
#            return "ORIG"
#
#        if self.building.targ is None:
#            return "TARG"
#
#        if self.building.kind == "MOVE":
#            if self.building.via_c is None and self.board.needs_via_c(self.building.orig, self.building.targ):
#                return "VIAC"
#            elif self.building.coast is None and not self.auto_coast():
#                return "COAST"
#
#        return "DONE"
#
#    kinds = {
#        "H":               "HOLD",
#        "HOL":             "HOLD",
#        "HOLD":            "HOLD",
#        "M":               "MOVE",
#        "MOV":             "MOVE",
#        "MOVE":            "MOVE",
#        "ATTACK":          "MOVE",
#        "MOVE (ATTACK)":   "MOVE",
#        "SH":              "SUPH",
#        "SUPPORT HOLD":    "SUPH",
#        "SUPPORT TO HOLD": "SUPH",
#        "SUPPORT A HOLD":  "SUPH",
#        "SM":              "SUPM",
#        "SUPPORT MOVE":    "SUPM",
#        "SUPPORT TO MOVE": "SUPM",
#        "SUPPORT A MOVE":  "SUPM",
#        "C":               "CONV",
#        "CON":             "CONV",
#        "CONVOY":          "CONV"
#    }
#
#    kind_codes = set(kinds.values())
#
#    def register_kind(self, s):
#        try:
#            self.building.kind = self.kinds[s]
#        except KeyError:
#            pass
#        else:
#            return
#
#        if s in self.kind_codes:
#            self.building.kind = s
#        else:
#            raise ValueError
#
#    def register_terr_list(self, s):
#        if s == "DONE":
#            if not self.terrs:
#                raise BuilderError("You must specify at least one territory")
#
#            self.terr_complete = True
#            self.more = False
#            return
#
#        if s == "REMOVE":
#            if not self.terrs:
#                raise ValueError
#
#            self.terr_remove = True
#            return
#
#        if s == "ADD":
#            self.terr_remove = False
#            self.more = False
#            return
#
#        try:
#            t = terr_names.match_case(s)
#        except KeyError:
#            raise ValueError
#
#        if self.terr_remove:
#            try:
#                self.terrs.remove(t)
#            except KeyError:
#                raise ValueError
#
#            if not self.terrs:
#                self.terr_remove = False
#        else:
#            self.validate_terr(t)
#
#            self.terrs.add(t)
#
#            if self.building.kind not in {"SUPH", "SUPM", "CONV"}:
#                self.terr_complete = True
#
#    def register_orig(self, s):
#        try:
#            t = terr_names.match_case(s)
#        except KeyError:
#            raise ValueError
#
#        self.validate_orig(t)
#
#        self.building.orig = t
#        self.more = False
#
#    def register_targ(self, s):
#        try:
#            t = terr_names.match_case(s)
#        except KeyError:
#            raise ValueError
#
#        self.validate_targ(t)
#
#        self.building.targ = t
#        self.more = False
#
#    def register_viac(self, s):
#        if s in {"YES", "Y"}:
#            self.building.via_c = True
#        elif s in {"NO", "N"}:
#            self.building.via_c = False
#        else:
#            raise ValueError
#
#    def register_coast(self, s):
#        if s in {"N", "NC", "(NC)", "NORTH", "NORTH COAST"}:
#            self.building.coast = "(NC)"
#        elif s in {"S", "SC", "(SC)", "SOUTH", "SOUTH COAST"}:
#            self.building.coast = "(SC)"
#        else:
#            raise ValueError
#
#    actions = {
#        "KIND":  lambda self, s: self.register_kind(s),
#        "TERR":  lambda self, s: self.register_terr_list(s),
#        "ORIG":  lambda self, s: self.register_orig(s),
#        "TARG":  lambda self, s: self.register_targ(s),
#        "VIAC":  lambda self, s: self.register_viac(s),
#        "COAST": lambda self, s: self.register_coast(s)
#    }
#
#    back_attrs = ["via_c", "coast", "targ", "orig", "terrs", "kind"]
#
#    def back(self):
#        for attr in self.back_attrs:
#            if attr != "terrs":
#                if getattr(self.building, attr) is not None:
#                    setattr(self.building, attr, None)
#                    break
#
#            elif self.terr_complete:
#                break
#
#        else:
#            raise IndexError
#
#        if attr in ["terrs", "kind"]:
#            self.terrs = set()
#            self.terr_complete = False
#
#        self.more = False
#        self.terr_remove = False
#
#    def push(self, s):
#        s = s.strip().upper()
#
#        ntf = self.next_to_fill()
#
#        if s == "BACK":
#            self.back()
#
#        elif s in {"MORE", "MORE..."}:
#            self.more = not self.more
#
#        elif ntf == "DONE":
#            raise IndexError
#
#        else:
#            self.actions[ntf](self, s)
#
#        return self.next_to_fill()
#
#    def validate_terr(self, t):
#        if not self.board[t].occupied:
#            raise BuilderError("There's no unit in " + t)
#
#        if self.board[t].occupied != self.nation:
#            raise BuilderError("You can't order someone else's unit")
#
#        if self.building.kind == "CONV":
#            if self.board[t].kind != "F":
#                raise BuilderError("Only fleets can convoy")
#
#            elif t not in offshore:
#                raise BuilderError("A fleet needs to be in open sea to convoy")
#
#
#        for o in self.orders:
#            if o.terr == t:
#                raise BuilderError("There's already another order for {} ({})".format(t, o))
#
#    def validate_orig(self, t):
#        if t in self.terrs:
#            raise BuilderError("{} is already part of the order".format(t))
#
#    def validate_targ(self, t):
#        t2 = self.terr if self.building.kind == "MOVE" else self.building.orig
#
#        if t == t2:
#            raise BuilderError("Can't move onto itself")
#
#    def ordered(self):
#        return {o.terr for o in self.orders}
#
#    def unordered(self):
#        return self.board.occupied(self.nation) - self.ordered()
#
#    def get_terrs_hint(self):
#        if self.terr_remove:
#            return self.terrs
#
#        available = self.unordered() - self.terrs
#
#        if self.building.kind == "CONV":
#            return available & offshore
#        else:
#            return available
#
#    def get_origs_hint(self):
#        ret = set()
#
#        if self.building.kind == "SUPM":
#            common_neighbors = copy(territories)
#
#            for t in self.terrs:
#                common_neighbors &= self.board.valid_dests(t)
#
#            for t in territories:
#                if (not self.board.valid_dests(t).isdisjoint(common_neighbors)
#                        or not self.board.valid_dests_via_c(t, self.terrs)
#                            .isdisjoint(common_neighbors)):
#
#                    ret.add(t)
#
#            ret -= self.terrs
#
#        elif self.building.kind == "CONV":
#            for t in sea_graph.neighbors(self.board.contiguous_fleets(self.terrs)):
#                if self.board[t].occupied and self.board[t].kind == "A":
#                    ret.add(t)
#
#        return ret
#
#    def get_targs_hint(self):
#        if self.building.kind == "MOVE":
#            return (self.board.valid_dests(self.terr)
#                    | self.board.valid_dests_via_c(self.building.orig))
#
#        if self.building.kind == "SUPH":
#            return self.board.valid_dests(self.terr)
#
#        elif self.building.kind == "SUPM":
#            common_neighbors = copy(territories)
#
#            for t in self.terrs:
#                common_neighbors &= self.board.valid_dests(t)
#
#            return (
#                common_neighbors & (
#                    self.board.valid_dests(self.building.orig)
#                    | self.board.valid_dests_via_c(
#                        self.building.orig, self.terrs)))
#
#        elif self.building.kind == "CONV":
#            return self.board.valid_dests_via_c(self.building.orig)
#
#
#    hints = {
#        "TERR": lambda self: self.get_terrs_hint(),
#        "ORIG": lambda self: self.get_origs_hint(),
#        "TARG": lambda self: self.get_targs_hint()
#    }
#
#    @staticmethod
#    def get_kind_keyboard():
#        return RKM([
#            ["Hold"],
#            ["Move (attack)"],
#            ["Support to Hold"],
#            ["Support to Move"],
#            ["Convoy"],
#            ["Back"]
#        ])
#
#    @staticmethod
#    def get_coasts_keyboard():
#        return RKM([
#            ["North", "South"],
#            ["Back"]
#        ])
#
#    @staticmethod
#    def get_yesno_keyboard():
#        return RKM([
#            ["Yes", "No"],
#            ["Back"]
#        ])
#
#    basic_keyboards = {
#        "KIND":  lambda self: self.get_kind_keyboard(),
#        "COAST": lambda self: self.get_coasts_keyboard(),
#        "VIAC":  lambda self: self.get_yesno_keyboard()
#    }
#
#    def get_keyboard(self):
#        ntf = self.next_to_fill()
#
#        try:
#            return self.basic_keyboards[ntf](self)
#        except KeyError:
#            pass
#
#        try:
#            hint = self.hints[ntf](self)
#        except KeyError:
#            return None
#
#        if self.more:
#            hint = territories - hint
#
#        keyboard = make_grid(sorted(hint, key=str.casefold))
#
#        keyboard.append(["More..."])
#
#        if ntf == "TERR" and self.terrs:
#            if not self.terr_remove:
#                keyboard.append(["Remove"])
#            else:
#                keyboard.append(["Add"])
#
#            keyboard.append(["Done"])
#
#        keyboard.append(["Back"])
#
#        return RKM(keyboard)
