# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2000-2004  Juan David Ibáñez Palomar <jdavid@itaapy.com>

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


# Import from Zope
from ImageFile import ImageFile
from DocumentTemplate.DT_String import String
import ZClasses
from Products.PageTemplates.GlobalTranslationService import \
     setGlobalTranslationService

# Import from Localizer
import Localizer, LocalContent, MessageCatalog, LocalFolder
from LocalFiles import LocalDTMLFile, LocalPageTemplateFile
from LocalPropertyManager import LocalPropertyManager, LocalProperty
from GettextTag import GettextTag


misc_ = {'arrow_left': ImageFile('img/arrow_left.gif', globals()),
         'arrow_right': ImageFile('img/arrow_right.gif', globals()),
         'eye_opened': ImageFile('img/eye_opened.gif', globals()),
         'eye_closed': ImageFile('img/eye_closed.gif', globals())}



class GlobalTranslationService:
    def translate(self, domain, msgid, *args, **kw):
        context = kw.get('context')
        if context is None:
            # Placeless!
            return msgid

        # Find it by acquisition
        translation_service = getattr(context, 'gettext', None)
        if translation_service is None:
            return msgid
        return translation_service.translate(domain, msgid, *args, **kw)



def initialize(context):
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
    setGlobalTranslationService(GlobalTranslationService())
