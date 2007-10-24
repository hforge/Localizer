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

# Import from the Standard Library
from cgi import escape
from cStringIO import StringIO
import md5
from types import StringType, UnicodeType
from xml.sax import make_parser, handler, InputSource

# Import from itools
from itools.datatypes import LanguageTag
from itools.tmx import TMX, Sentence, Message
from itools.xliff import XLIFF, Translation, File as xliff_File

# Import from Zope
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from Products.ZCatalog.CatalogPathAwareness import CatalogAware
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass, MessageDialog

# Import from Localizer
from LocalFiles import LocalDTMLFile
from LocalPropertyManager import LocalPropertyManager, LocalProperty
from utils import _


def md5text(str):
    """
    Create an MD5 sum (or hash) of a text. It is guaranteed to be 32 bytes
    long.
    """
    return md5.new(str.encode('utf-8')).hexdigest()


manage_addLocalContentForm = LocalDTMLFile('ui/LocalContent_add', globals())
def manage_addLocalContent(self, id, sourcelang, languages, REQUEST=None):
    """ """
    languages.append(sourcelang)   # Make sure source is one of the target langs
    self._setObject(id, LocalContent(id, sourcelang, tuple(languages)))

    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


class LocalContent(CatalogAware, LocalPropertyManager, PropertyManager,
                   SimpleItem):
    """ """

    meta_type = 'LocalContent'

    security = ClassSecurityInfo()

    # Properties metadata
    _local_properties_metadata = ({'id': 'title', 'type': 'string'},
                                  {'id': 'body', 'type': 'text'})

    _properties = ()

    title = LocalProperty('title')   # Override title from SimpleItem
    body = LocalProperty('body')


    def manage_options(self):
        """ """
        options = LocalContent.inheritedAttribute('manage_options')(self) \
                  + PropertyManager.manage_options[:1] \
                  + ({'label': u'Import', 'action': 'manage_import',
                         'help': ('Localizer', 'MC_importExport.stx')},
                     {'label': u'Export', 'action': 'manage_export',
                      'help': ('Localizer', 'MC_importExport.stx')}) \
                  + PropertyManager.manage_options[1:] \
                  + SimpleItem.manage_options

        r = []
        for option in options:
            option = option.copy()
            option['label'] = _(option['label'])
            r.append(option)

        return r


    def __init__(self, id, sourcelang, languages):
        self.id = id
        self._default_language = sourcelang
        self._languages = languages


    index_html = None     # Prevent accidental acquisition


    def __call__(self, client=None, REQUEST=None, RESPONSE=None, **kw):
        if REQUEST is None:
            REQUEST = self.REQUEST

        # Get the template to use
        template_id = 'default_template'
        if hasattr(self.aq_base, 'default_template'):
            template_id = self.default_template

        # Render the object
        template = getattr(self.aq_parent, template_id)
        template = template.__of__(self)
        return apply(template, ((client, self), REQUEST), kw)


    # Override some methods to be sure that LocalContent objects are
    # reindexed when changed.
    def set_localpropvalue(self, id, lang, value):
        LocalContent.inheritedAttribute('set_localpropvalue')(self, id, lang,
                                                              value)

        self.reindex_object()


    def del_localproperty(self, id):
        LocalContent.inheritedAttribute('del_localproperty')(self, id)

        self.reindex_object()

    security.declareProtected('View management screens', 'manage_import')
    manage_import = LocalDTMLFile('ui/LC_import_form', globals())

    #######################################################################
    # TMX support
    security.declareProtected('View management screens', 'manage_export')
    manage_export = LocalDTMLFile('ui/LC_export_form', globals())

    security.declareProtected('Manage messages', 'tmx_export')
    def tmx_export(self, REQUEST, RESPONSE=None):
        """
        Exports the content of the message catalog to a TMX file
        """
        langorg = self._default_language

        # build data structure for the xml header
        xml_header = {}
        xml_header['standalone'] = -1
        xml_header['xml_version'] = u'1.0'
        xml_header['document_type'] = (u'tmx',
                                       u'http://www.lisa.org/tmx/tmx14.dtd')
        # build data structure for the tmx header
        version = u'1.4'
        tmx_header = {}
        tmx_header['creationtool'] = u'Localizer'
        tmx_header['creationtoolversion'] = u'1.x'
        tmx_header['datatype'] = u'plaintext'
        tmx_header['segtype'] = u'paragraph'
        tmx_header['adminlang'] = u'%s' % langorg
        tmx_header['srclang'] = u'%s' % langorg
        tmx_header['o-encoding'] = u'utf-8'


        # Get the messages, and perhaps its translations.
        d = {}
        filename = '%s.tmx' % self.id

        for k in self._local_properties.keys():
            sentences = {}
            for lang in self._languages:
                trans, fuzzy = self.get_localproperty(k, lang)
                sentences[lang] = Sentence(trans, {'lang':lang})
            d[self.get_localproperty(k, langorg)[0]] = Message(sentences)

        tmx = TMX()
        tmx.build(xml_header, version, tmx_header, d)

        if RESPONSE is not None:
            RESPONSE.setHeader('Content-type','application/data')
            RESPONSE.setHeader('Content-Disposition',
                               'attachment; filename="%s"' % filename)

        return tmx.to_str()



    security.declareProtected('Manage messages', 'tmx_import')
    def tmx_import(self, file, REQUEST=None, RESPONSE=None):
        """ Imports a TMX level 1 file.
        """
        try:
            data = file.read()
            tmx = TMX(string=data)
        except:
            return MessageDialog(title = 'Parse error',
                               message = _('impossible to parse the file') ,
                               action = 'manage_import',)

        for (id, msg) in tmx.state.messages.items():
            for (prop, d) in self._local_properties.items():
                if d[self._default_language][0] == id:
                    msg.msgstr.pop(self._default_language)
                    for lang in msg.msgstr.keys():
                        # normalize the languageTag and extract the core
                        (core, local) = LanguageTag.decode(lang)
                        lang = LanguageTag.encode((core, local))
                        if lang not in self._languages:
                            self._languages += (lang,)
                        texte = msg.msgstr[lang].text
                        if texte:
                            self.set_localpropvalue(prop, lang, texte)
                            if core != lang and core != self._default_language:
                                if core not in self._languages:
                                    self._languages += (core,)
                                if not msg.msgstr.has_key(core):
                                    self.set_localpropvalue(prop, lang, texte)

        if REQUEST is not None:
            RESPONSE.redirect('manage_localPropertiesForm')



    security.declareProtected('Manage messages', 'xliff_export')
    def xliff_export(self, targetlang, export_all=1, REQUEST=None,
                     RESPONSE=None):
        """ Exports the content of the message catalog to an XLIFF file
        """
        orglang = self._default_language
        export_all = int(export_all)
        from DateTime import DateTime

        # Generate the XLIFF file header
        RESPONSE.setHeader('Content-Type', 'text/xml; charset=UTF-8')
        RESPONSE.setHeader('Content-Disposition',
           'attachment; filename="%s_%s_%s.xlf"' % ( self.id, orglang,
                                                     targetlang ))

        # build data structure for the xml header
        xml_header = {}
        xml_header['standalone'] = -1
        xml_header['xml_version'] = u'1.0'
        xml_header['document_type'] = (u'xliff',
              u'http://www.oasis-open.org/committees/xliff/documents/xliff.dtd')

        version = u'1.0'

        # build the data-stucture for the File tag
        attributes = {}
        attributes['original'] = u'/%s' % self.absolute_url(1)
        attributes['product-name'] = u'Localizer'
        attributes['product-version'] = u'1.1.x'
        attributes['data-type'] = u'plaintext'
        attributes['source-language'] = orglang
        attributes['target-language'] = targetlang
        attributes['date'] = DateTime().HTML4()

        # Get the messages, and perhaps its translations.
        d = {}

        for prop in self._local_properties.keys():
            target, fuzzy = self.get_localproperty(prop, targetlang)
            msgkey, fuzzy = self.get_localproperty(prop, self._default_language)
            # if export_all=1 export all messages otherwise export
            # only untranslated messages
            if export_all or not target:
                id = md5text(msgkey)
                if target:
                    t = Translation(msgkey, target, {'id':id})
                else:
                    t = Translation(msgkey, msgkey, {'id':id})
                d[msgkey] = t

        files = [xliff_File(d, attributes)]

        xliff = XLIFF()
        xliff.build(xml_header, version, files)

        return xliff.to_str()

    security.declareProtected('Manage messages', 'xliff_import')
    def xliff_import(self, file, REQUEST=None):
        """ XLIFF is the XML Localization Interchange File Format
            designed by a group of software providers.
            It is specified by www.oasis-open.org
        """
        try:
            data = file.read()
            xliff = XLIFF(string=data)
        except:
            return MessageDialog(title = 'Parse error',
                                 message = _('impossible to parse the file') ,
                                 action = 'manage_import',)

        num_trans = 0
        (file_ids, sources, targets) = xliff.get_languages()

        # update languages
        if len(sources) > 1 or sources[0] != self._default_language:
            return MessageDialog(title = 'Language error',
                                 message = _('incompatible language sources') ,
                                 action = 'manage_import',)
        for lang in targets:
            if lang != self._default_language and lang not in self._languages:
                self._languages += (lang,)

        # get messages
        for file in xliff.state.files:
            cur_target = file.attributes.get('target-language', '')
            for msg in file.body.keys():
                for (prop, val) in self._local_properties.items():
                    if val[self._default_language][0] == msg:
                        if cur_target and file.body[msg].target:
                            texte = file.body[msg].target
                            self.set_localpropvalue(prop, cur_target, texte)
                            num_trans += 1

        if REQUEST is not None:
            return MessageDialog(
                title = _(u'Messages imported'),
                message = (_(u'Imported %d messages to %s') %
                           (num_trans, ' '.join(targets))),
                action = 'manage_localPropertiesForm')


InitializeClass(LocalContent)
