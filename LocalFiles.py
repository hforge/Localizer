# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2000-2003  Juan David Ibáñez Palomar <jdavid@itaapy.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.


__revision__ = "$Id: LocalFiles.py,v 1.10 2004/03/15 17:36:09 roug Exp $"


"""
Localizer

This module provides several localized classes, that is, classes with the
locale attribute. Currently it only defines the classes LocalDTMLFile and
LocalPageTemplateFile, which should be used instead of DTMLFile and
PageTemplateFile.
"""


# Import Python modules
from gettext import GNUTranslations
import os

# Import Zope modules
from Globals import DTMLFile, package_home

# Import Localizer modules
from Utils import lang_negotiator


translations = {}


def get_translations(localedir, language=None):
    """
    Looks the <language>.mo file in <localedir> and returns a
    GNUTranslations instance for it. If <language> is None uses
    the language negotiator to guess the user preferred language.
    """
    # Initialize the product translations
    locale = localedir
    if not translations.has_key(locale):
        translations[locale] = None

    if translations[locale] is None:
        translations[locale] = {}
        # Load .mo files
        for filename in [ x for x in os.listdir(locale) if x.endswith('.mo') ]:
            lang = filename[:-3]
            filename = os.path.join(locale, filename)
            f = open(filename, 'rb')
            translations[locale][lang] = GNUTranslations(f)
            f.close()

    # Get the translations to use
    ptranslations = translations[locale]

    if language is None:
        # Builds the list of available languages
        available_languages = ptranslations.keys()

        # Get the language!
        lang = lang_negotiator(available_languages)
    else:
        lang = None

    return ptranslations.get(lang or language, None)


def gettext(self, message, language=None):
    """ """
    # Get the translations to use
    translations = get_translations(self.locale, language)

    if translations is not None:
        return translations.ugettext(message)

    return message

ugettext = gettext   # XXX backwards compatibility


class LocalDTMLFile(DTMLFile):
    def __init__(self, name, _prefix=None, **kw):
        apply(LocalDTMLFile.inheritedAttribute('__init__'),
              (self, name, _prefix), kw)
        self.locale = os.path.join(package_home(_prefix), 'locale')

    def _exec(self, bound_data, args, kw):
        # Add our gettext first
        bound_data['gettext'] = self.gettext
        bound_data['ugettext'] = self.ugettext  # XXX backwards compatibility
        return apply(LocalDTMLFile.inheritedAttribute('_exec'),
                     (self, bound_data, args, kw))

    gettext = gettext
    ugettext = ugettext  # XXX backwards compatibility


# Zope Page Templates (ZPT)
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
            self.locale = os.path.join(package_home(_prefix), 'locale')

        def _exec(self, bound_data, args, kw):
            # Add our gettext first
            bound_data['gettext'] = self.gettext
            bound_data['ugettext'] = self.ugettext # XXX backwards compatibility
            return apply(LocalPageTemplateFile.inheritedAttribute('_exec'),
                         (self, bound_data, args, kw))

        gettext = gettext
        ugettext = ugettext  # XXX backwards compatibility
