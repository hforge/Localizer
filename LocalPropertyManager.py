# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2000-2003  Juan David Ibáñez Palomar <jdavid@itaapy.com>
#               2003  Itaapy <contact@itaapy.com>
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


__revision__ = "$Id: LocalPropertyManager.py,v 1.41 2003/08/12 16:14:35 jdavid Exp $" 




# Import Python modules
from urllib import quote

# Import Zope modules
from AccessControl import ClassSecurityInfo
import Globals

# Localizer
import Gettext
from LanguageManager import LanguageManager
from LocalAttributes import LocalAttribute, LocalAttributesBase
from LocalFiles import LocalDTMLFile


# To translate.
_ = Gettext.translation(globals())
N_ = Gettext.dummy


# XXX
# For backwards compatibility (<= 0.8.0): other classes import 'LocalProperty'
LocalProperty = LocalAttribute


class LocalPropertyManager(LanguageManager, LocalAttributesBase):
    """
    Mixin class that allows to manage localized properties.
    Somewhat similar to OFS.PropertyManager.
    """

    security = ClassSecurityInfo()

    # Metadata for local properties
    # Example: ({'id': 'title', 'type': 'string'},)
    _local_properties_metadata = ()

    # Local properties are stored here
    # Example: {'title': {'en': 'Title', 'es': 'Título'}}
    _local_properties = {}

    # Useful to find or index all LPM instances
    isLocalPropertyManager = 1


    def getLocalPropertyManager(self):
        """
        Returns the instance, useful to get the object through acquisition.
        """
        return self


    def manage_options(self):
        """ """
        if self.need_upgrade():
            # This instance needs to be upgraded
            options = ({'label': N_('Upgrade'), 'action': 'manage_upgradeForm',
                        'help': ('Localizer', 'LPM_upgrade.stx')},)
        else:
            options = ()

        return options \
               + ({'label': N_('Local properties'),
                   'action': 'manage_localPropertiesForm',
                   'help': ('Localizer', 'LPM_properties.stx')},) \
               + LanguageManager.manage_options


    security.declarePublic('hasLocalProperty')
    def hasLocalProperty(self, id):
        """Return true if object has a property 'id'"""
        for property in self._local_properties_metadata:
            if property['id'] == id:
                return 1
        return 0


    security.declareProtected('View management screens',
                              'manage_localPropertiesForm')
    manage_localPropertiesForm = LocalDTMLFile('ui/LPM_properties', globals())


    security.declarePublic('get_batch_size')
    def get_batch_size(self):
        """
        Returns the size of the batch for the web interface.
        For now it's a constant value.
        """
        return 5


    security.declarePublic('get_batch_size')
    def get_batch_start(self, start, index):
        """
        Returns the right batch_start, used in the web interfaces.
        """
        # Get the size of the batch
        size = self.get_batch_size()

        start2 = index - size + 1
        if start2 < 0:
            start2 = 0

        if start < start2:
            return start2

        return start


    security.declarePublic('get_url')
    def get_url(self, url, batch_start, batch_index, lang_hide, **kw):
        """
        Used in the 'localPropertiesForm' to generate the urls.
        """
        params = []
        for key, value in kw.items():
            params.append('%s=%s' % (key, quote(value)))

        params.extend(['batch_start:int=%d' % batch_start,
                       'batch_index:int=%d' % batch_index])

        for lang in lang_hide:
            params.append('lang_hide:tuple=%s' % lang)


        return url + '?' + '&amp;'.join(params)


    security.declareProtected('Manage properties', 'set_localpropvalue')
    def set_localpropvalue(self, id, lang, value):
        properties = self._local_properties.copy()
        if not properties.has_key(id):
            properties[id] = {}

        properties[id][lang] = value

        self._local_properties = properties


    security.declareProtected('Manage properties', 'set_localproperty')
    def set_localproperty(self, id, type, lang=None, value=None):
        """Adds a new local property"""
        if not self.hasLocalProperty(id):
            self._local_properties_metadata += ({'id': id, 'type': type},)
            setattr(self, id, LocalProperty(id))

        if lang is not None:
            self.set_localpropvalue(id, lang, value)


    security.declareProtected('Manage properties', 'del_localproperty')
    def del_localproperty(self, id):
        """Deletes a property"""
        # update properties metadata
        p = [ x for x in self._local_properties_metadata if x['id'] != id ]
        self._local_properties_metadata = tuple(p)

        # delete attribute
        try:
            del self._local_properties[id]
        except KeyError:
            pass

        try:
            delattr(self, id)
        except KeyError:
            pass


    # XXX Backwards compatibility
    _setLocalPropValue = set_localpropvalue
    _setLocalProperty = set_localproperty
    _delLocalProperty = del_localproperty



    security.declareProtected('Manage properties', 'manage_addLocalProperty')
    def manage_addLocalProperty(self, id, type, REQUEST=None, RESPONSE=None):
        """Adds a new local property"""
        self.set_localproperty(id, type)

        if RESPONSE is not None:
            url = "%s/manage_localPropertiesForm" % REQUEST['URL1']

            batch_start = REQUEST['batch_start']
            batch_index = len(self._local_properties_metadata) - 1
            batch_start = self.get_batch_start(batch_start, batch_index)
            lang_hide = REQUEST.get('lang_hide', ())

            url = self.get_url(url, batch_start, batch_index, lang_hide,
                               manage_tabs_message=_('Saved changes.'))
            RESPONSE.redirect(url)


    security.declareProtected('Manage properties', 'manage_editLocalProperty')
    def manage_editLocalProperty(self, id, REQUEST, RESPONSE=None):
        """Edit a property"""
        for lang in self.get_languages():
            if REQUEST.has_key(lang):
                self.set_localpropvalue(id, lang, REQUEST[lang].strip())

        if RESPONSE is not None:
            url = "%s/manage_localPropertiesForm" % REQUEST['URL1']
            url = self.get_url(url,
                               REQUEST['batch_start'], REQUEST['batch_index'],
                               REQUEST.get('lang_hide', ()),
                               manage_tabs_message=_('Saved changes.'))
            RESPONSE.redirect(url)


    security.declareProtected('Manage properties', 'manage_delLocalProperty')
    def manage_delLocalProperty(self, id, REQUEST=None, RESPONSE=None):
        """Deletes a property"""
        self.del_localproperty(id)

        if RESPONSE is not None:
            url = "%s/manage_localPropertiesForm" % REQUEST['URL1']

            batch_start = REQUEST['batch_start']
            batch_index = REQUEST['batch_index']
            batch_index = min(batch_index,
                              len(self._local_properties_metadata) - 1)
            batch_start = self.get_batch_start(batch_start, batch_index)
            lang_hide = REQUEST.get('lang_hide', ())

            url = self.get_url(url, batch_start, batch_index, lang_hide,
                               manage_tabs_message=_('Saved changes.'))
            RESPONSE.redirect(url)



    security.declarePublic('getLocalProperties')
    def getLocalProperties(self):
        """Returns a copy of the properties metadata."""
        return tuple([ x.copy() for x in self._local_properties_metadata ])


    security.declarePublic('getLocalAttribute')
    def getLocalAttribute(self, id, lang=None):
        """Returns a local property"""
        try:
            property = self._local_properties[id]
        except KeyError:
            return ''  # What should be returned here??

        # No language, look for the first non-empty available version
        if lang is None:
            lang = self.get_selected_language(property=id)

        try:
            return property[lang]
        except KeyError:
            return ''   # What should be returned here??


    # For backwards compatibility (<= 0.8.0)
    getLocalProperty = getLocalAttribute


    # Languages logic
    security.declarePublic('get_available_languages')
    def get_available_languages(self, **kw):
        """ """
        languages = self.get_languages()
        id = kw.get('property', None)
        if id is None:
            # Is this thing right??
            return languages
        else:
            property = self._local_properties[id]
            return [ x for x in languages if property.get(x, None) ]


    security.declarePublic('get_default_language')
    def get_default_language(self):
        """ """
        if self._default_language:
            return self._default_language

        languages = self.get_languages()
        if languages:
            return languages[0]

        return None


    # Upgrading..
    security.declarePublic('need_upgrade')
    def need_upgrade(self):
        """ """
        return hasattr(self.aq_base, 'original_language')
        

    manage_upgradeForm = LocalDTMLFile('ui/LPM_upgrade', globals())
    def manage_upgrade(self, REQUEST=None, RESPONSE=None):
        """ """
        # In version 0.6 appears the attribute "_languages"
        if not self.__dict__.has_key('_languages'):
            try:
                localizer = self.Localizer
            except AttributeError:
                self._languages = ('en',)
            else:
                self._languages = tuple(localizer.get_supported_languages())

            for property in self._local_properties_metadata:
                id = property['id']
                setattr(self, id, LocalProperty(id))

        # In version 0.7 the language management logic moved to the
        # mixin class LanguageManager, as a consequence the attribute
        # "original_language" changes its name to "_default_language".
        if hasattr(self.aq_base, 'original_languge'):
            self._default_language = self.original_language
            del self.original_language

        if REQUEST is not None:
            return self.manage_main(self, REQUEST)


    # Define <id>_<lang> attributes, useful for example to catalog
    def __getattr__(self, name):
        try:
            index = name.rfind('_')
            id, lang = name[:index], name[index+1:]
            property = self._local_properties[id]
        except:
            raise AttributeError, "%s instance has no attribute '%s'" \
                                  % (self.__class__.__name__, name)

        return property.get(lang, '')
 


Globals.InitializeClass(LocalPropertyManager)
