# -*- coding: UTF-8 -*-
# Copyright (C) 2000-2004  Juan David Ibáñez Palomar <jdavid@itaapy.com>
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

# Import from the Standard Library
from urlparse import urlparse

# Import from itools
from itools.i18n import Multilingual, get_language_name, get_languages

# Import from Zope
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

# Import from Localizer
from LocalFiles import LocalDTMLFile
from utils import lang_negotiator


class LanguageManager(Multilingual):
    """ """

    security = ClassSecurityInfo()

    manage_options = ({'label': u'Languages', 'action': 'manage_languages',
                       'help': ('Localizer', 'LM_languages.stx')},)


    ########################################################################
    # API
    ########################################################################

    # Security settings
    security.declarePublic('get_languages')
    security.declareProtected('Manage languages', 'set_languages')
    security.declareProtected('Manage languages', 'add_language')
    security.declareProtected('Manage languages', 'del_language')
    security.declarePublic('get_languages_mapping')


    security.declarePublic('get_language_name')
    def get_language_name(self, id=None):
        """
        Returns the name of the given language code.

        XXX Kept here for backwards compatibility only
        """
        if id is None:
            id = self.get_default_language()
        return get_language_name(id)


    security.declarePublic('get_available_languages')
    security.declarePublic('get_default_language')


    # XXX Kept here temporarily, further refactoring needed
    security.declarePublic('get_selected_language')
    def get_selected_language(self, **kw):
        """
        Returns the selected language. Here the language negotiation takes
        place.

        Accepts keyword arguments which will be passed to
        'get_available_languages'.
        """
        available_languages = apply(self.get_available_languages, (), kw)

        return lang_negotiator(available_languages) \
               or self.get_default_language()


    ########################################################################
    # ZMI
    ########################################################################
    security.declareProtected('View management screens', 'manage_languages')
    manage_languages = LocalDTMLFile('ui/LM_languages', globals())


    security.declarePublic('get_all_languages')
    def get_all_languages(self):
        """
        Returns all ISO languages, used by 'manage_languages'.
        """
        return get_languages()


    security.declareProtected('Manage languages', 'manage_addLanguage')
    def manage_addLanguage(self, language, REQUEST=None, RESPONSE=None):
        """ """
        self.add_language(language)

        if RESPONSE is not None:
            RESPONSE.redirect("%s/manage_languages" % REQUEST['URL1'])


    security.declareProtected('Manage languages', 'manage_delLanguages')
    def manage_delLanguages(self, languages, REQUEST, RESPONSE):
        """ """
        for language in languages:
            self.del_language(language)

        RESPONSE.redirect("%s/manage_languages" % REQUEST['URL1'])


    security.declareProtected('Manage languages', 'manage_changeDefaultLang')
    def manage_changeDefaultLang(self, language, REQUEST=None, RESPONSE=None):
        """ """
        self._default_language = language

        if REQUEST is not None:
            RESPONSE.redirect("%s/manage_languages" % REQUEST['URL1'])


    # Unicode support, custom ZMI
    manage_page_header = LocalDTMLFile('ui/manage_page_header', globals())


InitializeClass(LanguageManager)
