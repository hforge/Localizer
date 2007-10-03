# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2000-2005  Juan David Ibáñez Palomar <jdavid@itaapy.com>
#               2003  Roberto Quero, Eduardo Corrales
#               2004  Søren Roug
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

"""
This module provides the MessageCatalog base class, which
provides message catalogs for the web.
"""

# Import from the Standard Library
import base64, md5
import codecs
import re
import sys
import time
from types import StringType, UnicodeType
from urllib import quote
from xml.sax import make_parser, handler, InputSource
from cStringIO import StringIO
from cgi import escape

# Import from itools
from itools.datatypes import LanguageTag
from itools.gettext import PO
from itools.tmx import TMX, Sentence, Message, Note
from itools.xliff import XLIFF, Translation, Note as xliff_Note, \
    File as xliff_File

# Import from Zope
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from DocumentTemplate.DT_Util import ustr
from Globals import  MessageDialog, PersistentMapping, InitializeClass
from OFS.ObjectManager import ObjectManager
from OFS.SimpleItem import SimpleItem
from TAL.TALInterpreter import interpolate

# Import from Localizer
from LanguageManager import LanguageManager
from LocalFiles import LocalDTMLFile
from utils import charsets, lang_negotiator, _



def md5text(str):
    """
    Create an MD5 sum (or hash) of a text. It is guaranteed to be 32 bytes
    long.
    """
    return md5.new(str.encode('utf-8')).hexdigest()


manage_addMessageCatalogForm = LocalDTMLFile('ui/MC_add', globals())
def manage_addMessageCatalog(self, id, title, languages, sourcelang=None,
                             REQUEST=None):
    """ """
    if sourcelang is None:
        sourcelang = languages[0]

    self._setObject(id, MessageCatalog(id, title, sourcelang, languages))

    if REQUEST is not None:
        return self.manage_main(self, REQUEST)


# Empty header information for PO files, the default
# UTF-8 is the encoding by default
empty_po_header = {'last_translator_name': '',
                   'last_translator_email': '',
                   'language_team': '',
                   'charset': 'UTF-8'}

_marker = []


class MessageCatalog(LanguageManager, ObjectManager, SimpleItem):
    """
    Stores messages and their translations...
    """

    meta_type = 'MessageCatalog'

    security = ClassSecurityInfo()


    def __init__(self, id, title, sourcelang, languages):
        self.id = id

        self.title = title

        # Language Manager data
        self._languages = tuple(languages)
        self._default_language = sourcelang

        # Here the message translations are stored
        self._messages = PersistentMapping()

        # Data for the PO files headers
        self._po_headers = PersistentMapping()
        for lang in self._languages:
            self._po_headers[lang] = empty_po_header


    #######################################################################
    # Public API
    #######################################################################
    security.declarePublic('message_encode')
    def message_encode(self, message):
        """
        Encodes a message to an ASCII string.
        To be used in the user interface, to avoid problems with the
        encodings, HTML entities, etc..
        """
        if type(message) is UnicodeType:
            msg = 'u' + message.encode('utf8')
        else:
            msg = 'n' + message

        return base64.encodestring(msg)


    security.declarePublic('message_decode')
    def message_decode(self, message):
        """
        Decodes a message from an ASCII string.
        To be used in the user interface, to avoid problems with the
        encodings, HTML entities, etc..
        """
        message = base64.decodestring(message)
        type = message[0]
        message = message[1:]
        if type == 'u':
            return unicode(message, 'utf8')
        return message


    security.declarePublic('message_exists')
    def message_exists(self, message):
        """ """
        return self._messages.has_key(message)


    security.declareProtected('Manage messages', 'message_edit')
    def message_edit(self, message, language, translation, note):
        """ """
        self._messages[message][language] = translation
        self._messages[message]['note'] = note


    security.declareProtected('Manage messages', 'message_del')
    def message_del(self, message):
        """ """
        del self._messages[message]


    security.declarePublic('gettext')
    def gettext(self, message, lang=None, add=1, default=_marker):
        """Returns the message translation from the database if available.

        If add=1, add any unknown message to the database.
        If a default is provided, use it instead of the message id
        as a translation for unknown messages.
        """

        if type(message) not in (StringType, UnicodeType):
            raise TypeError, 'only strings can be translated.'

        message = message.strip()

        if default is _marker:
            default = message

        # Add it if it's not in the dictionary
        if add and not self._messages.has_key(message) and message:
            self._messages[message] = PersistentMapping()

        # Get the string
        if self._messages.has_key(message):
            m = self._messages[message]

            if lang is None:
                # Builds the list of available languages
                # should the empty translations be filtered?
                available_languages = list(self._languages)

                # Imagine that the default language is 'en'. There is no
                # translation from 'en' to 'en' in the message catalog
                # The user has the preferences 'en' and 'nl' in that order
                # The next two lines make certain 'en' is shown, not 'nl'
                if not self._default_language in available_languages:
                    available_languages.append(self._default_language)

                # Get the language!
                lang = lang_negotiator(available_languages)

                # Is it None? use the default
                if lang is None:
                    lang = self._default_language

            if lang is not None:
                return m.get(lang) or default

        return default


    __call__ = gettext


    def translate(self, domain, msgid, *args, **kw):
        """
        This method is required to get the i18n namespace from ZPT working.
        """
        msgstr = self.gettext(msgid)
        mapping = kw.get('mapping')
        return interpolate(msgstr, mapping)


    #######################################################################
    # Management screens
    #######################################################################
    def manage_options(self):
        """ """
        options = (
            {'label': u'Messages', 'action': 'manage_messages',
             'help': ('Localizer', 'MC_messages.stx')},
            {'label': u'Properties', 'action': 'manage_propertiesForm'},
            {'label': u'Import', 'action': 'manage_Import_form',
             'help': ('Localizer', 'MC_importExport.stx')},
            {'label': u'Export', 'action': 'manage_Export_form',
             'help': ('Localizer', 'MC_importExport.stx')}) \
            + LanguageManager.manage_options \
            + SimpleItem.manage_options

        r = []
        for option in options:
            option = option.copy()
            option['label'] = _(option['label'])
            r.append(option)

        return r


    #######################################################################
    # Management screens -- Messages
    #######################################################################
    security.declareProtected('Manage messages', 'manage_messages')
    manage_messages = LocalDTMLFile('ui/MC_messages', globals())


    security.declareProtected('Manage messages', 'get_translations')
    def get_translations(self, message):
        """ """
        return self._messages[message]


    security.declarePublic('get_url')
    def get_url(self, url, batch_start, batch_size, regex, lang, empty, **kw):
        """ """
        params = []
        for key, value in kw.items():
            if value is not None:
                params.append('%s=%s' % (key, quote(value)))

        params.extend(['batch_start:int=%d' % batch_start,
                       'batch_size:int=%d' % batch_size,
                       'regex=%s' % quote(regex),
                       'empty=%s' % (empty and 'on' or '')])

        if lang:
            params.append('lang=%s' % lang)

        return url + '?' + '&amp;'.join(params)

    def to_unicode(self, x):
        """
        In Zope the ISO-8859-1 encoding has an special status, normal strings
        are considered to be in this encoding by default.
        """
        if type(x) is StringType:
            x = unicode(x, 'iso-8859-1')
        return x


    def filter_sort(self, x, y):
        x = self.to_unicode(x)
        y = self.to_unicode(y)
        return cmp(x, y)


    security.declarePublic('filter')
    def filter(self, message, lang, empty, regex, batch_start, batch_size=15):
        """
        For the management interface, allows to filter the messages to show.
        """
        # Filter the messages
        regex = regex.strip()

        try:
            regex = re.compile(regex)
        except:
            regex = re.compile('')

        messages = []
        for m, t in self._messages.items():
            if regex.search(m) and (not empty or not t.get(lang, '').strip()):
                messages.append(m)
        messages.sort(self.filter_sort)

        # How many messages
        n = len(messages)

        # Calculate the start
        while batch_start >= n:
            batch_start = batch_start - batch_size

        if batch_start < 0:
            batch_start = 0

        # Select the batch to show
        batch_end = batch_start + batch_size
        messages = messages[batch_start:batch_end]

        # Get the message
        message_encoded = None
        if message is None:
            if messages:
                message = messages[0]
                message_encoded = self.message_encode(message)
        else:
            message_encoded = message
            message = self.message_decode(message)

        # Calculate the current message
        aux = []
        for x in messages:
            current = type(x) is type(message) \
                      and self.to_unicode(x) == self.to_unicode(message)
            aux.append({'message': x, 'current': current})

        return {'messages': aux,
                'n_messages': n,
                'batch_start': batch_start,
                'message': message,
                'message_encoded': message_encoded}


    security.declareProtected('Manage messages', 'manage_editMessage')
    def manage_editMessage(self, message, language, translation, note,
                           REQUEST, RESPONSE):
        """Modifies a message."""
        message_encoded = message
        message = self.message_decode(message_encoded)
        self.message_edit(message, language, translation, note)

        url = self.get_url(REQUEST.URL1 + '/manage_messages',
                           REQUEST['batch_start'], REQUEST['batch_size'],
                           REQUEST['regex'], REQUEST.get('lang', ''),
                           REQUEST.get('empty', 0),
                           msg=message_encoded,
                           manage_tabs_message=_(u'Saved changes.'))
        RESPONSE.redirect(url)


    security.declareProtected('Manage messages', 'manage_delMessage')
    def manage_delMessage(self, message, REQUEST, RESPONSE):
        """ """
        message = self.message_decode(message)
        self.message_del(message)

        url = self.get_url(REQUEST.URL1 + '/manage_messages',
                           REQUEST['batch_start'], REQUEST['batch_size'],
                           REQUEST['regex'], REQUEST.get('lang', ''),
                           REQUEST.get('empty', 0),
                           manage_tabs_message=_(u'Saved changes.'))
        RESPONSE.redirect(url)



    #######################################################################
    # Management screens -- Properties
    # Management screens -- Import/Export
    # FTP access
    #######################################################################
    security.declareProtected('View management screens',
                              'manage_propertiesForm')
    manage_propertiesForm = LocalDTMLFile('ui/MC_properties', globals())


    security.declareProtected('View management screens', 'manage_properties')
    def manage_properties(self, title, REQUEST=None, RESPONSE=None):
        """Change the Message Catalog properties."""
        self.title = title

        if RESPONSE is not None:
            RESPONSE.redirect('manage_propertiesForm')


    # Properties management screen
    security.declareProtected('View management screens', 'get_po_header')
    def get_po_header(self, lang):
        """ """
        # For backwards compatibility
        if not hasattr(aq_base(self), '_po_headers'):
            self._po_headers = PersistentMapping()

        return self._po_headers.get(lang, empty_po_header)


    security.declareProtected('View management screens', 'update_po_header')
    def update_po_header(self, lang,
                         last_translator_name=None,
                         last_translator_email=None,
                         language_team=None,
                         charset=None,
                         REQUEST=None, RESPONSE=None):
        """ """
        header = self.get_po_header(lang)

        if last_translator_name is None:
            last_translator_name = header['last_translator_name']

        if last_translator_email is None:
            last_translator_email = header['last_translator_email']

        if language_team is None:
            language_team = header['language_team']

        if charset is None:
            charset = header['charset']

        header = {'last_translator_name': last_translator_name,
                  'last_translator_email': last_translator_email,
                  'language_team': language_team,
                  'charset': charset}

        self._po_headers[lang] = header

        if RESPONSE is not None:
            RESPONSE.redirect('manage_propertiesForm')



    security.declareProtected('View management screens', 'manage_Import_form')
    manage_Import_form = LocalDTMLFile('ui/MC_Import_form', globals())


    security.declarePublic('get_charsets')
    def get_charsets(self):
        """ """
        return charsets[:]


    security.declarePublic('manage_export')
    def manage_export(self, x, REQUEST=None, RESPONSE=None):
        """
        Exports the content of the message catalog either to a template
        file (locale.pot) or to an language specific PO file (<x>.po).
        """
        # Get the PO header info
        header = self.get_po_header(x)
        last_translator_name = header['last_translator_name']
        last_translator_email = header['last_translator_email']
        language_team = header['language_team']
        charset = header['charset']

        # PO file header, empty message.
        po_revision_date = time.strftime('%Y-%m-%d %H:%m+%Z',
                                         time.gmtime(time.time()))
        pot_creation_date = po_revision_date
        last_translator = '%s <%s>' % (last_translator_name,
                                       last_translator_email)

        if x == 'locale.pot':
            language_team = 'LANGUAGE <LL@li.org>'
        else:
            language_team = '%s <%s>' % (x, language_team)

        r = ['msgid ""',
             'msgstr "Project-Id-Version: %s\\n"' % self.title,
             '"POT-Creation-Date: %s\\n"' % pot_creation_date,
             '"PO-Revision-Date: %s\\n"' % po_revision_date,
             '"Last-Translator: %s\\n"' % last_translator,
             '"Language-Team: %s\\n"' % language_team,
             '"MIME-Version: 1.0\\n"',
             '"Content-Type: text/plain; charset=%s\\n"' % charset,
             '"Content-Transfer-Encoding: 8bit\\n"',
             '', '']


        # Get the messages, and perhaps its translations.
        d = {}
        if x == 'locale.pot':
            filename = x
            for k in self._messages.keys():
                d[k] = ""
        else:
            filename = '%s.po' % x
            for k, v in self._messages.items():
                try:
                    d[k] = v[x]
                except KeyError:
                    d[k] = ""

        # Generate the file
        def backslashescape(x):
            quote_esc = re.compile(r'"')
            x = quote_esc.sub('\\"', x)

            trans = [('\n', '\\n'), ('\r', '\\r'), ('\t', '\\t')]
            for a, b in trans:
                x = x.replace(a, b)

            return x

        # Generate sorted msgids to simplify diffs
        dkeys = d.keys()
        dkeys.sort()
        for k in dkeys:
            r.append('msgid "%s"' % backslashescape(k))
            v = d[k]
            r.append('msgstr "%s"' % backslashescape(v))
            r.append('')

        if RESPONSE is not None:
            RESPONSE.setHeader('Content-type','application/data')
            RESPONSE.setHeader('Content-Disposition',
                               'inline;filename=%s' % filename)

        r2 = []
        for x in r:
            if type(x) is UnicodeType:
                r2.append(x.encode(charset))
            else:
                r2.append(x)

        return '\n'.join(r2)


    security.declareProtected('Manage messages', 'po_import')
    def po_import(self, lang, data):
        """ """
        messages = self._messages

        # Load the data
        po = PO(string=data)
        for msgid in po.get_msgids():
            if msgid:
                msgstr = po.get_msgstr(msgid) or ''
                if not messages.has_key(msgid):
                    messages[msgid] = PersistentMapping()
                messages[msgid][lang] = msgstr

        # Set the encoding (the full header should be loaded XXX)
        self.update_po_header(lang, charset=po.get_encoding())


    security.declareProtected('Manage messages', 'manage_import')
    def manage_import(self, lang, file, REQUEST=None, RESPONSE=None):
        """ """
        # XXX For backwards compatibility only, use "po_import" instead.
        if isinstance(file, str):
            content = file
        else:
            content = file.read()

        self.po_import(lang, content)

        if RESPONSE is not None:
            RESPONSE.redirect('manage_messages')


    def objectItems(self, spec=None):
        """ """
        for lang in self._languages:
            if not hasattr(aq_base(self), lang):
                self._setObject(lang, POFile(lang))

        r = MessageCatalog.inheritedAttribute('objectItems')(self, spec)
        return r


    #######################################################################
    # TMX support
    security.declareProtected('View management screens', 'manage_Export_form')
    manage_Export_form = LocalDTMLFile('ui/MC_Export_form', globals())


    security.declareProtected('Manage messages', 'tmx_export')
    def tmx_export(self, REQUEST, RESPONSE=None):
        """
        Exports the content of the message catalog to a TMX file
        """
        orglang = self._default_language
        
        # Get the header info
        header = self.get_po_header(orglang)
        charset = header['charset']
        
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
        tmx_header['adminlang'] = u'%s' % orglang
        tmx_header['srclang'] = u'%s' % orglang
        tmx_header['o-encoding'] = u'%s' % charset.lower()

        # handle messages
        d = {}
        filename = '%s.tmx' % self.id
        for msgkey, transunit in self._messages.items():
            sentences = {}
            for lang in transunit.keys():
                if lang != 'note':
                    s = Sentence(transunit[lang], {'lang':'%s'%lang})
                    sentences[lang] = s
                    
            if orglang not in transunit.keys():
                s = Sentence(msgkey, {'lang':'%s' % orglang})
                sentences[orglang] = s
            
            if transunit.has_key('note'):
                d[msgkey] = Message(sentences, {}, 
                                    [Note(transunit.get('note'))])
            else:
                d[msgkey] = Message(sentences)

        tmx = TMX()
        tmx.build(xml_header, version, tmx_header, d)

                
        if RESPONSE is not None:
            RESPONSE.setHeader('Content-type','application/data')
            RESPONSE.setHeader('Content-Disposition',
                               'attachment; filename="%s"' % filename)

        return tmx.to_str()        



    security.declareProtected('Manage messages', 'tmx_import')
    def tmx_import(self, howmuch, file, REQUEST=None, RESPONSE=None):
        """ Imports a TMX level 1 file.
        """
        try:
            data = file.read()
            tmx = TMX(string=data)
        except:
            return MessageDialog(title = 'Parse error',
                                 message = _('impossible to parse the file') ,
                                 action = 'manage_Import_form',) 
            
        num_notes = 0
        num_trans = 0
        
        if howmuch == 'clear':
            # Clear the message catalogue prior to import
            self._messages = {}
            self._languages = ()
            self._default_language = tmx.get_srclang()

        for (id, msg) in tmx.state.messages.items():
            if not self._messages.has_key(id) and howmuch == 'existing':
                pass
            else:
                msg.msgstr.pop(self._default_language)
                if not self._messages.has_key(id):
                    self._messages[id] = {}
                for lang in msg.msgstr.keys():
                    # normalize the languageTag and extract the core
                    (core, local) = LanguageTag.decode(lang)
                    lang = LanguageTag.encode((core, local))
                    if lang not in self._languages:
                        self._languages += (lang,)
                    if msg.msgstr[lang].text:    
                        self._messages[id][lang] = msg.msgstr[lang].text
                        if core != lang and core != self._default_language:
                            if core not in self._languages:
                                self._languages += (core,)
                            if not msg.msgstr.has_key(core):
                                self._messages[id][core] = msg.msgstr[lang].text
                if msg.notes:
                    ns = [m.text for m in msg.notes]
                    self._messages[id]['note'] = u' '.join(ns)
                    num_notes += 1
                num_trans += 1
                
        if REQUEST is not None:
            return MessageDialog(
                title = _(u'Messages imported'),
                message = _(u'Imported %d messages and %d notes')
                          % (num_trans, num_notes),
                action = 'manage_messages')
                    


    #######################################################################
    # Backwards compatibility (XXX)
    #######################################################################

    hasmsg = message_exists
    hasLS = message_exists  # CMFLocalizer uses it

    security.declareProtected('Manage messages', 'xliff_export')
    def xliff_export(self, x, export_all=1, REQUEST=None, RESPONSE=None):
        """ Exports the content of the message catalog to an XLIFF file
        """
        orglang = self._default_language
        export_all = int(export_all)
        from DateTime import DateTime
        
        # Generate the XLIFF file header
        RESPONSE.setHeader('Content-Type', 'text/xml; charset=UTF-8')
        RESPONSE.setHeader('Content-Disposition',
                           'attachment; filename="%s_%s_%s.xlf"' % (self.id,
                                                                    orglang,
                                                                    x))
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
        attributes['target-language'] = x
        attributes['date'] = DateTime().HTML4()

        # Get the messages, and perhaps its translations.
        d = {}
        for msgkey, transunit in self._messages.items():
            target = transunit.get(x, '')
            # if export_all=1 export all messages otherwise export
            # only untranslated messages
            if export_all or not target:
                id = md5text(msgkey)
                notes = []
                if transunit.has_key('note') and transunit['note']:
                    notes = [xliff_Note(transunit['note'])]
                if target:
                    t = Translation(msgkey, target, {'id':id}, notes)
                else:
                    t = Translation(msgkey, msgkey, {'id':id}, notes)
                d[msgkey] = t

        files = [xliff_File(d, attributes)]

        xliff = XLIFF()
        xliff.build(xml_header, version, files)

        return xliff.to_str()

    security.declareProtected('Manage messages', 'xliff_import')
    def xliff_import(self, howmuch, file, REQUEST=None):
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
                                 action = 'manage_Import_form',)

        num_notes = 0
        num_trans = 0
        (file_ids, sources, targets) = xliff.get_languages()

        if howmuch == 'clear':
            # Clear the message catalogue prior to import
            self._messages = {}
            self._languages = ()
            self._default_language = sources[0]

        # update languages
        if len(sources) > 1 or sources[0] != self._default_language:
            return MessageDialog(title = 'Language error',
                                 message = _('incompatible language sources') ,
                                 action = 'manage_Import_form',) 
        for lang in targets:
            if lang != self._default_language and lang not in self._languages:
                self._languages += (lang,)

        # get messages
        for file in xliff.state.files:
            cur_target = file.attributes.get('target-language', '')
            for msg in file.body.keys():
                if not self._messages.has_key(msg) and howmuch == 'existing':
                    pass
                else:
                    if not self._messages.has_key(msg):
                        self._messages[msg] = {}
                    
                    if cur_target and file.body[msg].target:
                        self._messages[msg][cur_target] = file.body[msg].target
                        num_trans += 1
                    if file.body[msg].notes:
                        ns = [n.text for n in file.body[msg].notes] 
                        comment = ' '.join(ns)
                        self._messages[msg]['note'] = comment
                        num_notes += 1
                        
        if REQUEST is not None:
            return MessageDialog(
                title = _(u'Messages imported'),
                message = (_(u'Imported %d messages and %d notes to %s') % \
                           (num_trans, num_notes, ' '.join(targets))),
                action = 'manage_messages')



class POFile(SimpleItem):
    """ """

    security = ClassSecurityInfo()


    def __init__(self, id):
        self.id = id


    security.declareProtected('FTP access', 'manage_FTPget')
    def manage_FTPget(self):
        """ """
        return self.manage_export(self.id)


    security.declareProtected('Manage messages', 'PUT')
    def PUT(self, REQUEST, RESPONSE):
        """ """
        body = REQUEST['BODY']
        self.po_import(self.id, body)
        RESPONSE.setStatus(204)
        return RESPONSE

InitializeClass(MessageCatalog)
InitializeClass(POFile)
