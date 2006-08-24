# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2000-2005  Juan David Ib��ez Palomar <jdavid@itaapy.com>
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
This Zope product is a hotfix, it dynamically applies several patches
to Zope.
"""

# Import from the Standard Library
import os
import pprint
from StringIO import StringIO as originalStringIO

# Import from itools
from itools import web
from itools.web import get_context

# Import from Zope
import Globals
from Products.PageTemplates.PageTemplate import getEngine, PageTemplate, \
     PTRuntimeError
from Products.PageTemplates import TALES
from TAL.TALInterpreter import TALInterpreter
from zLOG import LOG, ERROR, INFO, PROBLEM, DEBUG
from ZPublisher import Publish


# Flag
patch = False
Z_DEBUG_MODE = os.environ.get('Z_DEBUG_MODE') == '1'

# PATCH 1: Global Request
#
# The original purpose was to get the request object from places where the
# acquisition was disabled (within the __of__ method for example). It was
# inspired by the Tim McLaughlin's GlobalGetRequest proposal, see
# http://dev.zope.org/Wikis/DevSite/Proposals/GlobalGetRequest
#
# Currently it keeps a Context instance, which wraps the request object,
# but also other things, like the user's session, as it is required by
# the ikaaro CMS.
#
# The context objects are stored in a dictionary in the Publish module,
# whose keys are the thread id.
#
# Also, we keep the get_request method in the Globals module for backwards
# compatibility (with TranslationService for example).

def new_publish(zope_request, module_name, after_list, debug=0):
    # Build the Context instance, a wrapper around the Zope request
    web.zope2.init(zope_request)

    try:
        # Publish
        x = Publish.zope_publish(zope_request, module_name, after_list, debug)
    finally:
        # Remove the context object.
        # When conflicts occur the "publish" method is called again,
        # recursively. In this situation the context dictionary would
        # be cleaned in the innermost call, hence outer calls find the
        # context does not exists anymore. For this reason we check first
        # wether the context is there or not.
        if web.context.has_context():
            web.context.del_context()

    return x


if patch is False:
    # Apply the patch
    Publish.zope_publish = Publish.publish
    Publish.publish = new_publish

    # First import (it's not a refresh operation).
    # We need to apply the patches.
    patch = True

    # Add get_request for backwards compatibility
    def get_request():
        context = get_context()
        if context is None:
            return None
        return context.request.zope_request
    Globals.get_request = get_request



# PATCH 2: Unicode
#
# Enables support of Unicode in ZPT.
# For Zope 2.5.1 (unsupported), patch appropriately.
# For Zope 2.6b1+
#   - if LOCALIZER_USE_ZOPE_UNICODE, use standard Zope Unicode handling,
#   - otherwise use Localizer's version of StringIO for ZPT and TAL.

# XXX Simplify, only 2.8 is supported

patch_251 = not hasattr(TALInterpreter, 'StringIO')

if patch_251:
    try:
        # Patched 2.5.1 should have ustr in __builtins__
        ustr
    except NameError:
        LOG('Localizer', PROBLEM,
            'A Unicode-aware version of Zope is needed by Localizer to'
            ' apply its Unicode patch. Please consult the documentation'
            ' for a patched version of Zope 2.5.1, or use Zope 2.6b1 or'
            ' later.')
    else:
        # 3.1 - Fix two instances where ustr must be used
        def evaluateText(self, expr):
            text = self.evaluate(expr)
            if text is TALES.Default or text is None:
                return text
            return ustr(text) # Use "ustr" instead of "str"
        TALES.Context.evaluateText = evaluateText

        def do_insertStructure_tal(self, (expr, repldict, block)):
            structure = self.engine.evaluateStructure(expr)
            if structure is None:
                return
            if structure is self.Default:
                self.interpret(block)
                return
            text = ustr(structure)  # Use "ustr" instead of "str"
            if not (repldict or self.strictinsert):
                # Take a shortcut, no error checking
                self.stream_write(text)
                return
            if self.html:
                self.insertHTMLStructure(text, repldict)
            else:
                self.insertXMLStructure(text, repldict)
        TALInterpreter.do_insertStructure_tal = do_insertStructure_tal
        TALInterpreter.bytecode_handlers_tal["insertStructure"] = do_insertStructure_tal


# 3.2 - Fix uses of StringIO with a Unicode-aware StringIO

class LocalizerStringIO(originalStringIO):
    def write(self, s):
        if isinstance(s, unicode):
            response = get_request().RESPONSE
            try:
                s = response._encode_unicode(s)
            except AttributeError:
                # not an HTTPResponse
                pass
        originalStringIO.write(self, s)


if not patch_251:
    if os.environ.get('LOCALIZER_USE_ZOPE_UNICODE'):
        LOG('Localizer', DEBUG, 'No Unicode patching')
        # Use the standard Zope way of dealing with Unicode
    else:
        LOG('Localizer', DEBUG, 'Unicode patching for Zope 2.6b1+')
        # Patch the StringIO method of TALInterpreter and PageTemplate
        def patchedStringIO(self):
            return LocalizerStringIO()
        TALInterpreter.StringIO = patchedStringIO
        PageTemplate.StringIO = patchedStringIO

else:
    LOG('Localizer', DEBUG, 'Unicode patching for Zope 2.5.1')
    # Patch uses of StringIO in Zope 2.5.1
    def no_tag(self, start, program):
        state = self.saveState()
        self.stream = stream = LocalizerStringIO()
        self._stream_write = stream.write
        self.interpret(start)
        self.restoreOutputState(state)
        self.interpret(program)
    TALInterpreter.no_tag = no_tag

    def do_onError_tal(self, (block, handler)):
        state = self.saveState()
        self.stream = stream = LocalizerStringIO()
        self._stream_write = stream.write
        try:
            self.interpret(block)
        except self.TALESError, err:
            self.restoreState(state)
            engine = self.engine
            engine.beginScope()
            err.lineno, err.offset = self.position
            engine.setLocal('error', err)
            try:
                self.interpret(handler)
            finally:
                err.takeTraceback()
                engine.endScope()
        else:
            self.restoreOutputState(state)
            self.stream_write(stream.getvalue())
    TALInterpreter.do_onError_tal = do_onError_tal

    def pt_render(self, source=0, extra_context={}):
        """Render this Page Template"""
        if self._v_errors:
            raise PTRuntimeError, 'Page Template %s has errors.' % self.id
        output = LocalizerStringIO()
        c = self.pt_getContext()
        c.update(extra_context)
        if Z_DEBUG_MODE:
            __traceback_info__ = pprint.pformat(c)

        TALInterpreter(self._v_program, self._v_macros,
                       getEngine().getContext(c),
                       output,
                       tal=not source, strictinsert=0)()
        return output.getvalue()
    PageTemplate.pt_render = pt_render

del patch_251