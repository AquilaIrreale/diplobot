
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
