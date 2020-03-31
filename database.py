
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


from pathlib import Path
import sqlite3

from utils import qmarks
from orders import Order


schema = """
CREATE TABLE games (
    id INTEGER NOT NULL PRIMARY KEY,
    start_date INTEGER NOT NULL,
    game_date INTEGER NOT NULL,
    state TEXT NOT NULL
);
CREATE TABLE players (
    id INTEGER NOT NULL,
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    nation TEXT NOT NULL,
    ready BOOL NOT NULL,
    PRIMARY KEY (id, game_id)
);
CREATE TABLE units (
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    terr TEXT NOT NULL,
    type TEXT NOT NULL,
    owner INTEGER NOT NULL REFERENCES players(id),
    PRIMARY KEY (game_id, terr)
);
CREATE TABLE centers (
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    terr TEXT NOT NULL,
    player_id INTEGER NOT NULL REFERENCES players(id),
    PRIMARY KEY (game_id, terr)
);
CREATE TABLE orders (
    game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    player_id INTEGER NOT NULL REFERENCES players(id),
    type TEXT NOT NULL,
    unit TEXT NOT NULL,
    terr TEXT,
    orig TEXT,
    targ TEXT,
    coast TEXT,
    viac BOOL,
    PRIMARY KEY (game_id, player_id, terr)
);
"""


def load_schema():
    c = db.cursor()
    for stmt in schema.split(";"):
        if stmt := stmt.strip():
            c.execute(stmt)
    db.commit()


def enable_foreign_keys():
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = ON")
    db.commit()
    c.execute("PRAGMA foreign_keys")
    resp = c.fetchone()
    if resp is None or resp != (1,):
        raise RuntimeError("sqlite3 implementation doesn't support foreign keys")


def disable_foreign_keys():
    c = db.cursor()
    c.execute("PRAGMA foreign_keys = OFF")
    db.commit()


def store_orders(game_id, player_id, *orders):
    c = db.cursor()
    for order in orders:
        db_tuple = order.to_db_tuple()
        c.execute(
            "INSERT INTO orders"
            "(game_id, player_id, type, unit, terr, orig, targ, coast, viac) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (game_id, player_id, *db_tuple))
    db.commit()


def retrieve_orders(game_id, player_id=None, order_types=None):
    order_types = [
        (o.typestr if issubclass(o, Order) else o)
        for o in order_types
    ]

    query = (
        "SELECT type, unit, terr, orig, targ, coast, viac "
        "FROM orders "
        "WHERE game_id=?")
    params = (game_id,)

    if player_id is not None:
        query += " AND player_id=?"
        params += (player_id,)

    if order_types is not None:
        query += f" AND type IN ({qmarks(len(order_types))})"
        params += tuple(order_types)

    c = db.cursor()
    c.execute(query, params)
    while db_tuple := c.fetchone():
        yield Order.from_db_tuple(*db_tuple)


db_file = "diplobot.db"

db_exists = Path(db_file).exists()
db = sqlite3.connect(db_file)
enable_foreign_keys()

if not db_exists:
    load_schema()
