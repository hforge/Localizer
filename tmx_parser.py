# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2000-2004  Juan David Ib�ez Palomar <jdavid@itaapy.com>
#               2003  Roberto Quero, Eduardo Corrales
#               2004  Sren Roug
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

from xml.sax.handler import ContentHandler
from xml.sax import *
from types import StringType, UnicodeType


class HandleTMXParsing(handler.ContentHandler):
    """ Parse a TMX file
    """
    def __init__(self, tu_cb, header_cb):
        self.tu_cb = tu_cb
        self.header_cb = header_cb
        self.lang = ''
        self.__data = u''
        self.elements = {
         ('header'): (self.start_header,self.end_header),
         ('tu'): (self.start_tu,self.end_tu),
         ('tuv'): (self.start_tuv,self.end_tuv),
         ('seg'): (self.start_seg,self.end_seg),
         ('note'): (self.start_note,self.end_note),
          }

    def xmllang_attr(self, attrs):
        """ Check attributes for xml:lang and delete it
        """
        if attrs.has_key("xml:lang"):
            self.lang = attrs["xml:lang"]
#           del attrs["xml:lang"]

    def startElement(self, tag, attrs):
        """ This is the method called by SAX. We simply look
            up the tag in a list and then call the coresponding method
        """
        self.xmllang_attr(attrs)
        method = self.elements.get(tag, (None, None))[0]
        if method:
            method(tag,attrs)

    def endElement(self, tag):
        """ This is the method called by SAX. We simply look
            up the tag in a list and then call the coresponding method
        """
        method = self.elements.get(tag, (None, None))[1]
        if method:
            method(tag)

    def characters(self, text):
        """ This is the method called by SAX.
        """
        self.__data += text

    def start_header(self, tag, attrs):
        """ Start of header info
            We are mainly interested in the srclang info.
            We call a callback provided when the class was initialised
        """
        self.header_cb(attrs)

    def end_header(self,tag):
        """ Unused """
        pass

    def start_tu(self, tag, attrs):
        """ Translation unit """
        self.tudata = {}

    def end_tu(self,tag):
        self.tu_cb(self.tudata)

    def start_tuv(self, tag, attrs):
        """ Unused """
        pass

    def end_tuv(self,tag):
        """ Force the language to None, as the next tuv could have no xml:lang
            The correct way would be to stack the xml:lang so we fall back.
            But that is not how the TMX spec sees things.
        """
        self.lang = '*none*'

    def start_seg(self, tag, attrs):
        """ Start of segment """
        self.__data = u''

    def end_seg(self,tag):
        """ End of segment """
        self.tudata[self.lang] = self.__data

    def start_note(self, tag, attrs):
        """ Start of segment """
        self.__data = u''

    def end_note(self,tag):
        """ End of segment """
        self.tudata['_note'] = self.__data
