
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
import subprocess

from board import terr_names


def format_board(board):
    ret = "CLEAR ALL\n"

    for name, t in board.items():
        if t.occupied:
            coast = t.coast or ""
            ret += "{}{} {} {}\n".format(name, coast, t.kind, t.occupied)

    return ret


def format_orders(orders):
    ret = ""

    for o in orders:
        if o.kind != "HOLD":
            ret += str(o) + "\n"

    return ret


res_re = re.compile(r"^\d+: (SUCCEEDS|FAILS)$")

def parse_res(s):
    m = res_re.match(s)

    if not m:
        raise ValueError(s)

    return m.group(1) == "SUCCEEDS"


ret_re = re.compile(r"^(\w+):(( \w+)*)$")

def parse_ret(s):
    m = ret_re.match(s)

    if not m:
        raise ValueError(s)

    t1 = terr_names.match_case(m.group(1))

    g2 = m.group(2) or ""

    t2s = {terr_names.match_case(t) for t in g2.split()}

    return t1, t2s


def adjudicate(board, orders):
    payload = format_board(board) + "\n" + format_orders(orders) + "\n"

    cp = subprocess.run(
        ["cdippy"], input=payload, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, universal_newlines=True)

    if cp.stderr:
        raise ValueError(payload)

    lines = iter(cp.stdout.splitlines())

    resolutions = [None if o.kind == "HOLD" else parse_res(next(lines)) for o in orders]

    if next(lines):
        raise ValueError(payload)

    retreats = {t1: t2s for t1, t2s in (parse_ret(s) for s in lines if s)}

    for i, o in enumerate(orders):
        if o.kind == "HOLD":
            resolutions[i] = o.terr not in retreats

    return resolutions, retreats


