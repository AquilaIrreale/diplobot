
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
import subprocess
import xml.etree.ElementTree as ET

from copy import deepcopy
from tempfile import mkstemp

from board import supply_centers, split_coasts, Nation, UnitType, Terr, TerrCoast


nation_colors = {
    Nation.AUSTRIA: "#FE3A3A",
    Nation.ENGLAND: "#163BC7",
    Nation.FRANCE: "#00E9FF",
    Nation.GERMANY: "#878787",
    Nation.ITALY: "#00FF00",
    Nation.RUSSIA: "#BE68D6",
    Nation.TURKEY: "#F5F500"
}

board_master = ET.parse("assets/board.svg")

unit_re = re.compile(r"(?P<terr>\w{3})_(?P<kind>[AF])(_(?P<coast>NC|SC))?", re.I)
center_re = re.compile(r"(?P<terr>\w{3})_dot", re.I)


def set_style(e, key, value):
    style = e.get("style", default="")
    style, n = re.subn(rf"\b{key}:[^;]*", f"{key}:{value}", style, count=1)
    if not n:
        style = f"{key}:{value};{style}"
    e.set("style", style)


def del_style(e, key):
    style = e.get("style", default="")
    style = re.sub(rf"\b{key}:[^;]*;?", "", style)
    e.set("style", style)


for e in board_master.getroot().iter():
    if unit_re.fullmatch(e.get("id", default="").strip()):
        set_style(e, "display", "none")


def render_board(centers, units):
    centers = {Terr(t): n for t, n in centers.items()}
    units = {TerrCoast(tc): (n, k) for tc, (n, k) in units.items()}

    board_copy = deepcopy(board_master)
    root = board_copy.getroot()

    for e in board_copy.getroot().iter():
        id_attr = e.get("id", default="").strip()

        if m := center_re.fullmatch(id_attr):
            t = Terr(m.group("terr"))
            try:
                nation = centers[t]
            except KeyError:
                pass
            else:
                set_style(e, "fill", nation_colors[nation])

        elif m := unit_re.fullmatch(id_attr):
            tc = TerrCoast(m.group("terr"), m.group("coast"))
            k = UnitType(m.group("kind"))
            try:
                nation, kind = units[tc]
            except KeyError:
                pass
            else:
                if k == kind:
                    for f in e.iter():
                        set_style(f, "fill", nation_colors[nation])
                    del_style(e, "display")

    svg_fd, svg_fn = mkstemp(suffix=".svg")
    with os.fdopen(svg_fd, "wb") as f:
        board_copy.write(f)

    png_fd, png_fn = mkstemp(suffix=".png")
    os.close(png_fd)

    inkscape_process = subprocess.run(
        (
            f"inkscape",
            f"--export-filename={png_fn}",
            f"--export-type=png",
            f"--export-width=1280",
            f"--export-height=1175",
            svg_fn
        ))

    os.unlink(svg_fn)
    inkscape_process.check_returncode()

    #DEBUG
    subprocess.run(["sxiv", png_fn])

    return png_fn
