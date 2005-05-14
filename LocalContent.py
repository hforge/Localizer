# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2000-2004  Juan David Ibáñez Palomar <jdavid@itaapy.com>
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


# Import from the Standard Library
from cgi import escape
from types import StringType, UnicodeType
from xml.sax import make_parser, handler, InputSource
from cStringIO import StringIO

# Import from Zope
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager    
from Products.ZCatalog.CatalogPathAwareness import CatalogAware
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass, MessageDialog

# Import from iHotfix
from Products import iHotfix
from Products.iHotfix import N_

# Import from Localizer
from LocalFiles import LocalDTMLFile
from LocalPropertyManager import LocalPropertyManager, LocalProperty
from tmx_parser import HandleTMXParsing
from xliff_parser import HandleXliffParsing


_ = iHotfix.translation(globals())


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
                  + ({'label': 'View', 'action': ''},
                     {'label': N_('Import/Export'), 'action': 'manage_importExport',
                         'help': ('Localizer', 'MC_importExport.stx')},
                     {'label': N_('TMX'), 'action': 'manage_tmx'}) \
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

    security.declareProtected('View management screens', 'manage_importExport')
    manage_importExport = LocalDTMLFile('ui/LC_importExport', globals())

    #######################################################################
    # TMX support
    security.declareProtected('View management screens', 'manage_tmx')
    manage_tmx = LocalDTMLFile('ui/LC_tmx', globals())

    security.declareProtected('Manage messages', 'tmx_export')
    def tmx_export(self, REQUEST, RESPONSE=None):
        """
        Exports the content of the message catalog to a TMX file
        """
        messages = self._local_properties
        langorg = self._default_language
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
        r.append('adminlang="%s"' % langorg)
        r.append('srclang="%s"' % langorg)

        r.append('>')
        r.append('</header>')
        r.append('')

        # Get the messages, and perhaps its translations.
        d = {}
        filename = '%s.tmx' % self.id
        # Example: {'title': {'en': 'Title', 'es': 'Tï¿½ulo'}}
        for k, v in messages.items():
            try:
                d[k] = v[langorg]
            except KeyError:
                d[k] = ""

        # Generate sorted msgids to simplify diffs
        dkeys = d.keys()
        dkeys.sort()
        r.append('<body>')
        for k in dkeys:
            r.append('<tu>')
            for tlang in self._languages:
                value = messages.get(k)
                try:
                    v = value[tlang]
                except KeyError:
                    v = ""
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
        tukey = unit[src_lang]

        messages = self._local_properties
        newlanguages = []
        # Example: {'title': {'en': 'Title', 'es': 'Tï¿½ulo'}}
        key = None
        for k, v in messages.items():
            if v[src_lang] == tukey:
                key = k
        if key is None:
            # We didn't find a property where the source matches anything
            # in the translation unit, so we give up
            return

        for lang in unit.keys():
            # Since the messagecatalog's default language overrides our
            # source language anyway, we handle *all* correctly already.
            # In the test below *all* should not be allowed.
            if lang == '*all*' or lang == '*none*':
                lang = self._v_srclang
            (target_lang, core_lang) = self._normalize_lang(lang)
            # If the core language is not seen before then add it
            if core_lang not in self._languages and core_lang not in newlanguages:
                newlanguages.append(core_lang)
            # If the language+locality is not seen before then add it
            if target_lang not in self._languages and target_lang not in newlanguages:
                newlanguages.append(target_lang)
            # Add message for language+locality
            if target_lang != src_lang:
                messages[key][target_lang] = unit[target_lang]
            # Add message for core language
            if not (unit.has_key(core_lang) or core_lang == src_lang):
                messages[key][core_lang] = unit[target_lang]

        if len(newlanguages) != 0:
            self._languages = tuple(self._languages) + tuple(newlanguages)
        self._local_properties = messages

    security.declareProtected('Manage messages', 'tmx_import')
    def tmx_import(self, file, REQUEST=None, RESPONSE=None):
        """ Imports a TMX level 1 file.
            We use the SAX parser. It has the benefit that it internally
            converts everything to python unicode strings.
        """
        self._v_srclang = self._default_language
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
            parser.parse(inputsrc)
        else:
            content = file.read()
            inputsrc.setByteStream(StringIO(content))
            parser.parse(inputsrc)

        if hasattr(self, '_v_srclang'):
            del self._v_srclang

        if REQUEST is not None:
            RESPONSE.redirect('manage_localPropertiesForm')

    security.declareProtected('Manage messages', 'xliff_export')
    def xliff_export(self, targetlang, export_all=1, REQUEST=None, RESPONSE=None):
        """ Exports the content of the message catalog to an XLIFF file
        """
        orglang = self._default_language
        messages = self._local_properties
#       orglang = orglang.lower()
        from DateTime import DateTime
        r = []
        r_append = r.append   #alias for append function. For optimization purposes
        # Generate the XLIFF file header
        RESPONSE.setHeader('Content-Type', 'text/xml; charset=UTF-8')
        RESPONSE.setHeader('Content-Disposition',
           'attachment; filename="%s_%s_%s.xlf"' % ( self.id, orglang, targetlang ))

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
        r_append('target-language="%s"' % targetlang)
        r_append('date="%s"' % DateTime().HTML4())
        r_append('>')
        r_append('<header>')
        r_append('</header>')
        r_append('<body>')

        # Get the messages, and perhaps its translations.
        d = {}
        # Example: {'title': {'en': 'Title', 'es': 'Tï¿½ulo'}}
        for k, v in messages.items():
            try:
                #if export_all=1 export all messages otherwise export only untranslated messages
                if int(export_all) == 1 or (int(export_all) == 0 and v[targetlang] == ''):
                    d[k] = v
            except KeyError:
                pass
        # Generate sorted msgids to simplify diffs
        dkeys = d.keys()
        dkeys.sort()
        for k in dkeys:
            r_append('<trans-unit id="%s">' % k)
            r_append(' <source>%s</source>' % escape(d[k][orglang]))
            r_append(' <target>%s</target>' % escape(d[k][targetlang]))
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

        messages = self._local_properties

        parser = HandleXliffParsing()

        #parse the xliff information
        chandler = parser.parseXLIFFFile(file)
        if chandler is None:
            return MessageDialog(title = 'Parse error',
             message = 'Unable to parse XLIFF file' ,
             action = 'manage_main',)

        header_info = chandler.getFileTag()
        #get the target language
        lang = [x for x in header_info if x[0]=='target-language'][0][1]
        (targetlang, core_lang) = self._normalize_lang(lang)

        body_info = chandler.getBody()

        num_notes = 0
        num_translations = 0
        #load the data
        for k, v in body_info.items():
            # If message is not in catalog, then it is new in xliff file -- not legal
            if messages.has_key(k):
                num_translations = num_translations + 1
                if v['target'] == u'' and v['source'] != srcmsg:
                # The source was translated. Happens sometimes
                    messages[k][targetlang] = v['source']
                else:
                    messages[k][targetlang] = v['target']

        if REQUEST is not None:
            return MessageDialog(title = _('Messages imported'),
             message = _('Imported %d messages and %d notes to %s') % \
                (num_translations, num_notes, targetlang) ,
             action = 'manage_localPropertiesForm',)


InitializeClass(LocalContent)
