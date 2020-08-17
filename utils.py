
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


from enum import Enum
from functools import wraps
from inspect import signature


class StrEnum(str, Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name


class UppercaseStrEnum(StrEnum):
    def __new__(cls, s):
        u = s.upper()
        obj = str.__new__(cls, u)
        obj._value_ = u
        return obj

    @classmethod
    def parse(cls, s):
        return cls(s.strip().upper())


def auto_repr(cls):
    self, *init_params = tuple(signature(cls.__init__).parameters.keys())
    def __repr__(self):
        attr_list = ", ".join(repr(getattr(self, a)) for a in init_params)
        return f"{cls.__name__}({attr_list})"
    cls.__repr__ = __repr__
    return cls


def casefold_mapping(it):
    return {
        s.casefold(): s
        for s in it
    }


def make_grid(l):
    r3 = len(l) % 3
    r4 = len(l) % 4

    if r4 == 0:
        cols = 4
    elif r3 == 0:
        cols = 3
    else:
        cols = 3 if r3 > r4 else 4

    return [l[i:i+cols] for i in range(0, len(l), cols)]
