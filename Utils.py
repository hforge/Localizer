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


# Import from itools
from itools.zope import get_context

# Import from Zope
from Globals import package_home


# Package home
ph = package_home(globals())


# Initializes a list with the charsets
charsets = [ x.strip() for x in open(ph + '/charsets.txt').readlines() ]



# Language negotiation
def lang_negotiator(available_languages):
    """
    Receives two ordered lists, the list of user preferred languages
    and the list of available languages. Returns the first user pref.
    language that is available, if none is available returns None.
    """
    context = get_context()
    request, response = context.request, context.response

    lang = request.accept_language.select_language(available_languages)

    # XXX Here we should set the Vary header, but, which value should it have??
##    response.set_header('Vary', 'accept-language')
##    response.set_header('Vary', '*')

    return lang


# Defines strings that must be internationalized
def N_(message): pass
N_('Contents')     # Tabs of the management screens
N_('View')
N_('Properties')
N_('Security')
N_('Undo')
N_('Ownership')
N_('Find')
# Languages
N_('Abkhazian')
N_('Afar')
N_('Afrikaans')
N_('Albanian')
N_('Amharic')
N_('Arabic')
N_('Armenian')
N_('Assamese')
N_('Aymara')
N_('Azerbaijani')
N_('Bashkir')
N_('Basque')
N_('Bengali')
N_('Bhutani')
N_('Bihari')
N_('Bislama')
N_('Bosnian')
N_('Breton')
N_('Bulgarian')
N_('Burmese')
N_('Belarusian')
N_('Cambodian')
N_('Catalan')
N_('Chinese')
N_('Chinese/China')
N_('Chinese/Taiwan')
N_('Cornish')
N_('Corsican')
N_('Croatian')
N_('Czech')
N_('Danish')
N_('Dutch')
N_('Dutch/Belgium')
N_('English')
N_('English/United Kingdom')
N_('English/United States')
N_('Esperanto')
N_('Estonian')
N_('Faroese')
N_('Fiji')
N_('Finnish')
N_('French')
N_('French/Belgium')
N_('French/Canada')
N_('French/France')
N_('French/Switzerland')
N_('Frisian')
N_('Galician')
N_('Georgian')
N_('German')
N_('German/Austria')
N_('German/Germany')
N_('German/Switzerland')
N_('Greek')
N_('Greenlandic')
N_('Guarani')
N_('Gujarati')
N_('Hausa')
N_('Hebrew')
N_('Hindi')
N_('Hungarian')
N_('Icelandic')
N_('Indonesian')
N_('Interlingua')
N_('Interlingue')
N_('Inuktitut')
N_('Inupiak')
N_('Irish')
N_('Italian')
N_('Japanese')
N_('Javanese')
N_('Kannada')
N_('Kashmiri')
N_('Kazakh')
N_('Kinyarwanda')
N_('Kirghiz')
N_('Kirundi')
N_('Korean')
N_('Kurdish')
N_('Laothian')
N_('Latin')
N_('Latvian')
N_('Lingala')
N_('Lithuanian')
N_('Luxembourgish')
N_('Macedonian')
N_('Malagasy')
N_('Malay')
N_('Malayalam')
N_('Maltese')
N_('Maori')
N_('Marathi')
N_('Moldavian')
N_('Mongolian')
N_('Nauru')
N_('Nepali')
N_('Northern Saami')
N_('Norwegian')
N_('Occitan')
N_('Oriya')
N_('Oromo')
N_('Pashto')
N_('Persian')
N_('Polish')
N_('Portuguese')
N_('Portuguese/Brazil')
N_('Punjabi')
N_('Quechua')
N_('Rhaeto-Romance')
N_('Romanian')
N_('Russian')
N_('Samoan')
N_('Sangho')
N_('Sanskrit')
N_('Scots Gaelic')
N_('Serbian')
N_('Serbo-Croatian')
N_('Sesotho')
N_('Setswana')
N_('Shona')
N_('Sindhi')
N_('Sinhalese')
N_('Siswati')
N_('Slovak')
N_('Slovenian')
N_('Somali')
N_('Spanish')
N_('Spanish/Argentina')
N_('Spanish/Colombia')
N_('Spanish/Mexico')
N_('Spanish/Spain')
N_('Sundanese')
N_('Swahili')
N_('Swedish')
N_('Tagalog')
N_('Tajik')
N_('Tamil')
N_('Tatar')
N_('Telugu')
N_('Thai')
N_('Tibetan')
N_('Tigrinya')
N_('Tonga')
N_('Tsonga')
N_('Turkish')
N_('Turkmen')
N_('Twi')
N_('Uighur')
N_('Ukrainian')
N_('Urdu')
N_('Uzbek')
N_('Vietnamese')
N_('Volapuk')
N_('Welsh')
N_('Wolof')
N_('Xhosa')
N_('Yiddish')
N_('Yoruba')
N_('Zhuang')
N_('Zulu')
