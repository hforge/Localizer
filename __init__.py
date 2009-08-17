# -*- coding: UTF-8 -*-
# Copyright (C) 2000-2005  Juan David Ibáñez Palomar <jdavid@itaapy.com>
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

# Check whether itools is installed
msg = ('itools 0.20 or later is needed, download from '
       'http://www.hforge.org/itools')
try:
    import itools
except ImportError:
    raise ImportError, msg
# Check itools is version 0.20 or later
if itools.__version__ < '0.20':
    raise ImportError, msg

# Import from the Standard Library
import os.path

# Import from Zope
from App.ImageFile import ImageFile
from DocumentTemplate.DT_String import String
import ZClasses
from Products.PageTemplates.GlobalTranslationService import \
     setGlobalTranslationService

# Import from Localizer
from patches import get_request
import Localizer, LocalContent, MessageCatalog, LocalFolder
from LocalFiles import LocalDTMLFile, LocalPageTemplateFile
from LocalPropertyManager import LocalPropertyManager, LocalProperty
from GettextTag import GettextTag



misc_ = {'arrow_left': ImageFile('img/arrow_left.gif', globals()),
         'arrow_right': ImageFile('img/arrow_right.gif', globals()),
         'eye_opened': ImageFile('img/eye_opened.gif', globals()),
         'eye_closed': ImageFile('img/eye_closed.gif', globals()),
         'obsolete': ImageFile('img/obsolete.gif', globals())}


class GlobalTranslationService:
    def __init__(self, service=None):
        if service is not None:
            self.pts_wrapper = PTSWrapper(service)
        else:
            self.pts_wrapper = None


    def translate(self, domain, msgid, *args, **kw):
        context = kw.get('context')
        if context is None:
            # Placeless!
            return msgid

        if domain is None or domain == 'default':
            domain = 'gettext'

        # Find it by acquisition
        translation_service = getattr(context, domain, None)

        # Try to get a catalog from a Localizer Object
        if translation_service is None:
            localizerObj = getattr(context, "Localizer", None)
            if localizerObj is not None:
                translation_service = getattr(localizerObj, domain, None)

        if translation_service is not None:
            from MessageCatalog import MessageCatalog
            if isinstance(translation_service, MessageCatalog):
                return translation_service.translate(domain, msgid, *args,
                                                     **kw)
        # Try PlacelessTranslationService
        if self.pts_wrapper is not None:
            return self.pts_wrapper.translate(domain, msgid, *args, **kw)

        return msgid


# Import from PlacelessTranslationService
try:
    from Products import PlacelessTranslationService
except ImportError:
    PTSWrapper = None
else:
    PTSWrapper = PlacelessTranslationService.PTSWrapper
    PlacelessTranslationService.PTSWrapper = GlobalTranslationService

# Try TranslationService
try:
    from Products import TranslationService
except ImportError:
    TranslationService = None


def initialize(context):
    # Check Localizer is not installed with a name different than Localizer
    # (this is a common mistake).
    filename = os.path.split(os.path.split(__file__)[0])[1]
    if filename != 'Localizer':
        message = (
            "The Localizer product must be installed within the 'Products'"
            " folder with the name 'Localizer' (not '%s').") % filename
        raise RuntimeError, message

    # XXX This code has been written by Cornel Nitu, it may be a solution to
    # upgrade instances.
##    root = context._ProductContext__app
##    for item in root.PrincipiaFind(root, obj_metatypes=['LocalContent'],
##                                   search_sub=1):
##        item[1].manage_upgrade()

    # Register the Localizer
    context.registerClass(Localizer.Localizer,
                          constructors = (Localizer.manage_addLocalizerForm,
                                          Localizer.manage_addLocalizer),
                          icon = 'img/localizer.gif')

    # Register LocalContent
    context.registerClass(
        LocalContent.LocalContent,
        constructors = (LocalContent.manage_addLocalContentForm,
                        LocalContent.manage_addLocalContent),
        icon='img/local_content.gif')

    # Register MessageCatalog
    context.registerClass(
        MessageCatalog.MessageCatalog,
        constructors = (MessageCatalog.manage_addMessageCatalogForm,
                        MessageCatalog.manage_addMessageCatalog),
        icon='img/message_catalog.gif')

    # Register LocalFolder
    context.registerClass(
        LocalFolder.LocalFolder,
        constructors = (LocalFolder.manage_addLocalFolderForm,
                        LocalFolder.manage_addLocalFolder),
        icon='img/local_folder.gif')

    # Register LocalPropertyManager as base class for ZClasses
    ZClasses.createZClassForBase(LocalPropertyManager, globals(),
                                 'LocalPropertyManager',
                                 'LocalPropertyManager')


    context.registerHelp()

    # Register the dtml-gettext tag
    String.commands['gettext'] = GettextTag

    # Register the global translation service for the i18n namespace (ZPT)
    if PTSWrapper is None and TranslationService is None:
        setGlobalTranslationService(GlobalTranslationService())
