
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
import os
import tempfile
import subprocess
import xml.etree.ElementTree as ET

from copy import deepcopy

from board import occupied, owned, supp_centers, split_coasts


def set_style(e, key, value):
    style = e.get("style", default="")

    if re.match(r"\b{}:".format(key), style):
        style = re.sub(r"\b{}:[^;]*".format(key), "{}:{}".format(key, value), style)

    else:
        if style:
            style += ';'

        style += "{}:{}".format(key, value)

    e.set("style", style)


def del_style(e, key):
    style = e.get("style", default="")
    style = re.sub(r"\b{}:[^;]*;?".format(key), "", style)
    e.set("style", style)


board_svg = ET.parse("board.svg")

piece_re = re.compile(r"^\w{3}_[AF](_(NC|SC))?$")

for e in board_svg.getroot().iter():
    if piece_re.match(e.get("id", default="")):
        set_style(e, "display", "none")


nation_colors = {
    "AUSTRIA" : "#FE3A3A",
    "ENGLAND" : "#163BC7",
    "FRANCE"  : "#00E9FF",
    "GERMANY" : "#878787",
    "ITALY"   : "#00FF00",
    "RUSSIA"  : "#BE68D6",
    "TURKEY"  : "#F5F500"
}


def render_board(board):
    board_copy = deepcopy(board_svg)
    root = board_copy.getroot()

    for t in owned(board) & supp_centers:
        e = root.find('.//*[@id="{}_dot"]'.format(t))
        color = nation_colors[board[t].owner]
        set_style(e, "fill", color)

    for t in occupied(board):
        k = board[t].kind
        c = board[t].coast

        piece_id = "{}_{}".format(t, k)

        if t in split_coasts and k == "F":
            piece_id += "_NC" if c == "(NC)" else "_SC"

        e = root.find('.//*[@id="{}"]/*'.format(piece_id))
        color = nation_colors[board[t].occupied]
        set_style(e, "fill", color)

        e = root.find('.//*[@id="{}"]'.format(piece_id))
        del_style(e, "display")

    svg_fd, svg_fn = tempfile.mkstemp()
    svg = os.fdopen(svg_fd, "wb")
    board_copy.write(svg)
    svg.close()

    png_fd, png_fn = tempfile.mkstemp()
    os.close(png_fd)

    subprocess.run(
        [
            "inkscape",
            "--export-png=" + png_fn,
            "--export-width=1280",
            "--export-height=1175",
            svg_fn
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

    os.unlink(svg_fn)

    return png_fn
