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


# Import from Python
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
from itools.resources import memory
from itools.gettext import PO

# Import from Zope
from AccessControl import ClassSecurityInfo
from Acquisition import aq_base
from Globals import  MessageDialog, PersistentMapping, InitializeClass
from OFS.ObjectManager import ObjectManager
from OFS.SimpleItem import SimpleItem

# Import from iHotfix
from Products import iHotfix

# Import from Localizer
from LanguageManager import LanguageManager
from LocalFiles import LocalDTMLFile
from Utils import charsets, lang_negotiator
from tmx_parser import HandleTMXParsing
from xliff_parser import HandleXliffParsing


_ = iHotfix.translation(globals())
N_ = iHotfix.dummy


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
        return self.gettext(msgid)


    #######################################################################
    # Management screens
    #######################################################################
    def manage_options(self):
        """ """
        options = (
            {'label': N_('Messages'), 'action': 'manage_messages',
             'help': ('Localizer', 'MC_messages.stx')},
            {'label': N_('Properties'), 'action': 'manage_propertiesForm'},
            {'label': N_('Import/Export'), 'action': 'manage_importExport',
             'help': ('Localizer', 'MC_importExport.stx')},
            {'label': N_('TMX'), 'action': 'manage_tmx'}) \
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
                           manage_tabs_message=_('Saved changes.'))
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
                           manage_tabs_message=_('Saved changes.'))
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



    security.declareProtected('View management screens', 'manage_importExport')
    manage_importExport = LocalDTMLFile('ui/MC_importExport', globals())


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

        resource = memory.File(data)
        po = PO.PO(resource)

        # Load the data
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
    security.declareProtected('View management screens', 'manage_tmx')
    manage_tmx = LocalDTMLFile('ui/MC_tmx', globals())


    security.declareProtected('Manage messages', 'tmx_export')
    def tmx_export(self, REQUEST, RESPONSE=None):
        """
        Exports the content of the message catalog to a TMX file
        """
        orglang = self._default_language
#       orglang = orglang.lower()

        # Get the header info
        header = self.get_po_header(orglang)
        charset = header['charset']

        r = []

        # Generate the TMX file header
        r.append('<?xml version="1.0" encoding="utf-8"?>')
        r.append('<!DOCTYPE tmx SYSTEM "http://www.lisa.org/tmx/tmx14.dtd">')
        r.append('<tmx version="1.4">')
        r.append('<header')
        r.append('creationtool="Localizer"')
        r.append('creationtoolversion="1.x"')
        r.append('datatype="plaintext"')
        r.append('segtype="paragraph"')
        r.append('adminlang="%s"' % orglang)
        r.append('srclang="%s"' % orglang)
        r.append('o-encoding="%s"' % charset.lower())

        r.append('>')
        r.append('</header>')
        r.append('')

        # Get the messages, and perhaps its translations.
        d = {}
        filename = '%s.tmx' % self.id
        for msgkey, transunit in self._messages.items():
            try:
                d[msgkey] = transunit[orglang]
            except KeyError:
                d[msgkey] = ""

        # Generate sorted msgids to simplify diffs
        dkeys = d.keys()
        dkeys.sort()
        r.append('<body>')
        for msgkey in dkeys:
            r.append('<tu>')
            transunit = self._messages.get(msgkey)
            if transunit.has_key('note') and transunit['note']:
                r.append('<note>%s</note>' % escape(transunit['note']))
            r.append('<tuv xml:lang="%s">' % orglang)
            # The key is the message
            r.append('<seg>%s</seg></tuv>' % escape(msgkey))

            for tlang in self._languages:
                if tlang != orglang:
                    v = transunit.get(tlang,'')
                    v = escape(v)
                    r.append('<tuv xml:lang="%s">' % tlang)
                    r.append('<seg>%s</seg></tuv>' % v)

            r.append('</tu>')
            r.append('')

        r.append('</body>')
        r.append('</tmx>')

        if RESPONSE is not None:
            RESPONSE.setHeader('Content-type','application/data')
            RESPONSE.setHeader('Content-Disposition',
                               'attachment; filename="%s"' % filename)

        r2 = []
        for x in r:
            if type(x) is UnicodeType:
                r2.append(x.encode('utf-8'))
            else:
                r2.append(x)

        return '\r\n'.join(r2)

    def _normalize_lang(self,langcode):
        """ Get the core language (The part before the '-') and return it
            in lowercase. If there is a local part, return it in uppercase.
        """
        dash = langcode.find('-')
        if dash == -1:
            la = langcode.lower()
            return (la,la)
        else:
            la = langcode[:dash].lower()
            lo = langcode[dash+1:].upper()
            return (la+'-'+lo,la)

    def _tmx_header(self, attrs):
        """ Works on a header (<header>)
        """
        if attrs.has_key('srclang'):
            self._v_srclang = attrs['srclang']

    def _tmx_tu(self, unit):
        """ Works on a translation unit (<tu>)
        """
        src_lang = self._default_language
        # We look up the message for the language we have chosen to be our
        # working language
        if unit.has_key(self._default_language):
            src_lang = self._default_language
        else:
            # This MUST exist. Otherwise the TMX file is bad
            src_lang = self._v_srclang
        key = unit[src_lang]
        if key == u'':
            return # Don't add empty messages
        keysum = md5text(key) # For future indexing on md5 sums

        messages = self._messages
        languages = list(self._languages)
        if not messages.has_key(key):
            if self._v_howmuch == 'clear' or self._v_howmuch == 'all':
                messages[key] = PersistentMapping()
            else:
                return # Don't add unknown messages

        self._v_num_translations = self._v_num_translations + 1

        for lang in unit.keys():
            # Since the messagecatalog's default language overrides our
            # source language anyway, we handle "*all*" correctly already.
            # In the test below "*all*" should not be allowed.
            # Languages that start with '_' are other properties
            if lang == '_note':
                messages[key]['note'] = unit[lang]
                self._v_num_notes = self._v_num_notes + 1
                continue
            if lang[0] == '_':  # Unknown special property
                continue
            if lang == '*all*' or lang == '*none*':
                lang = self._v_srclang
            (target_lang, core_lang) = self._normalize_lang(lang)
            # If the core language is not seen before then add it
            if core_lang != src_lang and core_lang not in languages:
                languages.append(core_lang)
            # If the language+locality is not seen before then add it
            if target_lang != src_lang and target_lang not in languages:
                languages.append(target_lang)
            # Add message for language+locality
            if target_lang != src_lang:
                messages[key][target_lang] = unit[target_lang]
            # Add message for core language
            if not (unit.has_key(core_lang) or core_lang == src_lang):
                messages[key][core_lang] = unit[target_lang]

        self._languages = tuple(languages)
        self._messages = messages

    security.declareProtected('Manage messages', 'tmx_import')
    def tmx_import(self, howmuch, file, REQUEST=None, RESPONSE=None):
        """ Imports a TMX level 1 file.
            We use the SAX parser. It has the benefit that it internally
            converts everything to python unicode strings.
        """
        if howmuch == 'clear':
            # Clear the message catalogue prior to import
            self._messages = {}
            self._languages = ()

        self._v_howmuch = howmuch
        self._v_srclang = self._default_language
        self._v_num_translations = 0
        self._v_num_notes = 0
        # Create a parser
        parser = make_parser()
        chandler = HandleTMXParsing(self._tmx_tu, self._tmx_header)
        # Tell the parser to use our handler
        parser.setContentHandler(chandler)
        # Don't load the DTD from the Internet
        parser.setFeature(handler.feature_external_ges, 0)
        inputsrc = InputSource()

        if type(file) is StringType:
            inputsrc.setByteStream(StringIO(file))
        else:
            content = file.read()
            inputsrc.setByteStream(StringIO(content))
        parser.parse(inputsrc)

        num_translations = self._v_num_translations
        num_notes = self._v_num_notes
        del self._v_srclang
        del self._v_howmuch
        del self._v_num_translations
        del self._v_num_notes

        if REQUEST is not None:
            return MessageDialog(
                title = _('Messages imported'),
                message = _('Imported %d messages and %d notes')
                          % (num_translations, num_notes),
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
        from DateTime import DateTime
        r = []
        # alias for append function. For optimization purposes
        r_append = r.append
        # Generate the XLIFF file header
        RESPONSE.setHeader('Content-Type', 'text/xml; charset=UTF-8')
        RESPONSE.setHeader('Content-Disposition',
                           'attachment; filename="%s_%s_%s.xlf"' % (self.id,
                                                                    orglang,
                                                                    x))

        r_append('<?xml version="1.0" encoding="UTF-8"?>')
        # Version 1.1 of the DTD is not yet available - use version 1.0
        r_append('<!DOCTYPE xliff SYSTEM "http://www.oasis-open.org/committees/xliff/documents/xliff.dtd">')
        # Force a UTF-8 char in the start
        r_append(u'<!-- XLIFF Format Copyright \xa9 OASIS Open 2001-2003 -->')
        r_append('<xliff version="1.0">')
        r_append('<file')
        r_append('original="/%s"' % self.absolute_url(1))
        r_append('product-name="Localizer"')
        r_append('product-version="1.1.x"')
        r_append('datatype="plaintext"')
        r_append('source-language="%s"' % orglang)
        r_append('target-language="%s"' % x)
        r_append('date="%s"' % DateTime().HTML4())
        r_append('>')
        r_append('<header>')
#       r_append('<phase-group>')
#       r_append('<phase ')
#       r_append('phase-name="%s"' % REQUEST.get('phase_name', ''))
#       r_append('process-name="Export"')
#       r_append('tool="Localizer"')
#       r_append('date="%s"' % DateTime().HTML4())
#       r_append('company-name="%s"' % REQUEST.get('company_name', ''))
#       r_append('job-id="%s"' % REQUEST.get('job_id', ''))
#       r_append('contact-name="%s"' % REQUEST.get('contact_name', ''))
#       r_append('contact-email="%s"' % REQUEST.get('contact_email', ''))
#       r_append('/>')
#       r_append('</phase-group>')
        r_append('</header>')
        r_append('<body>')

        # Get the messages, and perhaps its translations.
        d = {}
        for msgkey, transunit in self._messages.items():
            try:
                # if export_all=1 export all messages otherwise export
                # only untranslated messages
                if int(export_all) == 1 \
                       or (int(export_all) == 0 and transunit[x] == ''):
                    d[msgkey] = transunit[x]
            except KeyError:
                d[msgkey] = ""
            if d[msgkey] == "":
                d[msgkey] = msgkey
        # Generate sorted msgids to simplify diffs
        dkeys = d.keys()
        dkeys.sort()
        for msgkey in dkeys:
            transunit = self._messages[msgkey]
            r_append('<trans-unit id="%s">' % md5text(msgkey))
            r_append(' <source>%s</source>' % escape(msgkey))
            r_append(' <target>%s</target>' % escape(d[msgkey]))
            if transunit.has_key('note') and transunit['note']:
                r_append(' <note>%s</note>' % escape(transunit['note']))
            r_append('</trans-unit>')

        r_append('</body>')
        r_append('</file>')
        r_append('</xliff>')

        r2 = []
        for x in r:
            if type(x) is UnicodeType:
                r2.append(x.encode('utf-8'))
            else:
                r2.append(x)

        return '\r\n'.join(r2)

    security.declareProtected('Manage messages', 'xliff_import')
    def xliff_import(self, file, REQUEST=None):
        """ XLIFF is the XML Localization Interchange File Format
            designed by a group of software providers.
            It is specified by www.oasis-open.org
        """

        messages = self._messages

        # Build a table of messages hashed on the md5 sum of the message
        # This is because sometimes the xliff file has the sources translated,
        # not the targets
        md5hash = {}
        for mes in messages.keys():
            hash = md5text(mes)
            md5hash[hash] = mes

        parser = HandleXliffParsing()

        # parse the xliff information
        chandler = parser.parseXLIFFFile(file)
        if chandler is None:
            return MessageDialog(title = 'Parse error',
             message = 'Unable to parse XLIFF file' ,
             action = 'manage_main',)

        header_info = chandler.getFileTag()
        #get the target language
        lang = [x for x in header_info if x[0]=='target-language'][0][1]
        (targetlang, core_lang) = self._normalize_lang(lang)

        # return a dictionary {id: (source, target)}
        body_info = chandler.getBody()

        num_notes = 0
        num_translations = 0
        # load the data
        for msgkey, transunit in body_info.items():
            # If message is not in catalog, then it is new in xliff file
            # -- not legal
            if md5hash.has_key(msgkey):
                # Normal add
                srcmsg = md5hash[msgkey]
                if transunit['note'] != messages[srcmsg].get('note',u''):
                    messages[srcmsg]['note'] = transunit['note']
                    num_notes = num_notes + 1
                if srcmsg == transunit['target']:
                    # No translation was done
                    continue
                num_translations = num_translations + 1
                if transunit['target'] == u'' and transunit['source'] != srcmsg:
                # The source was translated. Happens sometimes
                    messages[srcmsg][targetlang] = transunit['source']
                else:
                    messages[srcmsg][targetlang] = transunit['target']

        if REQUEST is not None:
            return MessageDialog(title = _('Messages imported'),
             message = _('Imported %d messages and %d notes to %s') % \
                (num_translations, num_notes, targetlang) ,
             action = 'manage_messages',)


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
