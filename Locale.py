# Localizer, Zope product that provides internationalization services
# Copyright (C) 2000-2002  Juan David Ibáñez Palomar <j-david@noos.fr>

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""
LocalFolder
"""

__version__ = "$Revision: 1.2 $"


# Localizer
from LocalAttributes import LocalAttributes, LocalAttribute


class Locale(LocalAttributes):

    # Time, hours and minutes
    time = LocalAttribute('time')

    def time_en(self, datetime):
        return datetime.strftime('%H:%M')

    def time_es(self, datetime):
        return datetime.strftime('%H.%M')
