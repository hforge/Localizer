# -*- coding: UTF-8 -*-
# Copyright (C) 2000-2005 Juan David Ibáñez Palomar <jdavid@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Localizer

This module provides several localized classes, that is, classes with the
locale attribute. Currently it only defines the classes LocalDTMLFile and
LocalPageTemplateFile, which should be used instead of DTMLFile and
PageTemplateFile.
"""

# Import from the Standard Library
import os

# Import from itools
from itools import get_abspath
from itools.gettext import register_domain

# Import Zope modules
from Globals import DTMLFile

# Import from Localizer
from utils import DomainAware


class LocalDTMLFile(DTMLFile):

    def __init__(self, name, _prefix=None, **kw):
        apply(LocalDTMLFile.inheritedAttribute('__init__'),
              (self, name, _prefix), kw)

        domain = get_abspath(_prefix, 'locale')
        self.class_domain = domain
        register_domain(domain, domain)


    def _exec(self, bound_data, args, kw):
        # Add our gettext first
        bound_data['gettext'] = self.gettext
        bound_data['ugettext'] = self.gettext  # XXX backwards compatibility
        return apply(LocalDTMLFile.inheritedAttribute('_exec'),
                     (self, bound_data, args, kw))


    def gettext(self, message, language=None):
        return DomainAware.gettext(message, language, self.class_domain)



# Zope Page Templates (ZPT)
# XXX Deprecated, use the i18n namespace instead.
try:
    from Products.PageTemplates.PageTemplateFile import PageTemplateFile
except ImportError:
    # If ZPT is not installed
    class LocalPageTemplateFile:
        pass
else:
    class LocalPageTemplateFile(PageTemplateFile):

        def __init__(self, name, _prefix=None, **kw):
            apply(LocalPageTemplateFile.inheritedAttribute('__init__'),
                  (self, name, _prefix), kw)

            domain = get_abspath(_prefix, 'locale')
            self.class_domain = domain
            register_domain(domain, domain)


        def _exec(self, bound_data, args, kw):
            # Add our gettext first
            bound_data['gettext'] = self.gettext
            bound_data['ugettext'] = self.gettext # XXX backwards compatibility
            return apply(LocalPageTemplateFile.inheritedAttribute('_exec'),
                         (self, bound_data, args, kw))


        def gettext(self, message, language=None):
            return DomainAware.gettext(message, language, self.class_domain)
