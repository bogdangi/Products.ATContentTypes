#  ATContentTypes http://plone.org/products/atcontenttypes/
#  Archetypes reimplementation of the CMF core types
#  Copyright (c) 2003-2006 AT Content Types development team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""

"""
__author__  = 'Christian Heimes <tiran@cheimes.de>'
__docformat__ = 'restructuredtext'
__old_name__ = 'Products.ATContentTypes.types.ATDocument'

from types import TupleType

import time

from ZPublisher.HTTPRequest import HTTPRequest
from Products.CMFCore.permissions import View
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.utils import getToolByName
from AccessControl import ClassSecurityInfo
from ComputedAttribute import ComputedAttribute

from Products.CMFDefault.utils import SimpleHTMLParser

from Products.Archetypes.atapi import Schema
from Products.Archetypes.atapi import TextField
from Products.Archetypes.atapi import RichWidget
from Products.Archetypes.atapi import RFC822Marshaller
from Products.Archetypes.atapi import AnnotationStorage

from Products.ATContentTypes.configuration import zconf
from Products.ATContentTypes.config import PROJECTNAME
from Products.ATContentTypes.content.base import registerATCT
from Products.ATContentTypes.content.base import ATCTContent
from Products.ATContentTypes.content.base import updateActions
from Products.ATContentTypes.content.base import translateMimetypeAlias
from Products.ATContentTypes.content.schemata import ATContentTypeSchema
from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes.lib.historyaware import HistoryAwareMixin
from Products.ATContentTypes.interfaces import IATDocument

from Products.CMFPlone import PloneMessageFactory as _

ATDocumentSchema = ATContentTypeSchema.copy() + Schema((
    TextField('text',
              required=True,
              searchable=True,
              primary=True,
              storage = AnnotationStorage(migrate=True),
              validators = ('isTidyHtmlWithCleanup',),
              #validators = ('isTidyHtml',),
              default_output_type = 'text/x-html-safe',
              widget = RichWidget(
                        description = '',
                        label = _(u'label_body_text', default=u'Body Text'),
                        rows = 25,
                        allow_file_upload = zconf.ATDocument.allow_document_upload)),
    ), marshall=RFC822Marshaller()
    )
finalizeATCTSchema(ATDocumentSchema)

class ATDocument(ATCTContent, HistoryAwareMixin):
    """A page in the site. Can contain rich text."""

    schema         =  ATDocumentSchema

    content_icon   = 'document_icon.gif'
    meta_type      = 'ATDocument'
    portal_type    = 'Document'
    archetype_name = 'Page'
    default_view   = 'document_view'
    immediate_view = 'document_view'
    suppl_views    = ()
    _atct_newTypeFor = {'portal_type' : 'CMF Document', 'meta_type' : 'Document'}
    typeDescription= _(u'A page in the site. Can contain rich text.')
    assocMimetypes = ('application/xhtml+xml', 'message/rfc822', 'text/*',)
    assocFileExt   = ('txt', 'stx', 'rst', 'rest', 'py',)
    cmf_edit_kws   = ('text_format',)

    __implements__ = (ATCTContent.__implements__,
                      IATDocument,
                      HistoryAwareMixin.__implements__,
                     )

    security       = ClassSecurityInfo()

    actions = updateActions(ATCTContent,
                            HistoryAwareMixin.actions
                           )

    security.declareProtected(View, 'CookedBody')
    def CookedBody(self, stx_level='ignored'):
        """CMF compatibility method
        """
        return self.getText()


    security.declareProtected(ModifyPortalContent, 'EditableBody')
    def EditableBody(self):
        """CMF compatibility method
        """
        return self.getRawText()

    security.declareProtected(ModifyPortalContent,
                              'setFormat')
    def setFormat(self, value):
        """CMF compatibility method
        
        The default mutator is overwritten to:
        
          o add a conversion from stupid CMF content type (e.g. structured-text)
            to real mime types used by MTR.
        
          o Set format to default format if value is empty

        """
        if not value:
            value = zconf.ATDocument.default_content_type
        else:
            value = translateMimetypeAlias(value)
        ATCTContent.setFormat(self, value)

    security.declareProtected(ModifyPortalContent, 'setText')
    def setText(self, value, **kwargs):
        """Body text mutator
        
        * hook into mxTidy an replace the value with the tidied value
        """
        field = self.getField('text')
        # XXX this is ugly
        # When an object is initialized the first time we have to 
        # set the filename and mimetype.
        # In the case the value is empty/None we must not set the value because
        # it will overwrite uploaded data like a pdf file.
        if (value is None or value == ""):
            if not field.getRaw(self):
                # set mimetype and file name although the fi
                if 'mimetype' in kwargs and kwargs['mimetype']:
                    field.setContentType(self, kwargs['mimetype'])
                if 'filename' in kwargs and kwargs['filename']:
                    field.setFilename(self, kwargs['filename'])
            else:
                return

        # hook for mxTidy / isTidyHtmlWithCleanup validator
        tidyOutput = self.getTidyOutput(field)
        if tidyOutput:
            value = tidyOutput

        field.set(self, value, **kwargs) # set is ok

    text_format = ComputedAttribute(ATCTContent.getContentType, 1)

    security.declarePrivate('guessMimetypeOfText')
    def guessMimetypeOfText(self):
        """For ftp/webdav upload: get the mimetype from the id and data
        """
        mtr  = getToolByName(self, 'mimetypes_registry')
        id   = self.getId()
        data = self.getRawText()
        ext  = id.split('.')[-1]

        if ext != id:
            mimetype = mtr.classify(data, filename=ext)
        else:
            # no extension
            mimetype = mtr.classify(data)

        if not mimetype or (type(mimetype) is TupleType and not len(mimetype)):
            # nothing found
            return None

        if type(mimetype) is TupleType and len(mimetype):
            mimetype = mimetype[0]
        return mimetype.normalized()

    security.declarePrivate('getTidyOutput')
    def getTidyOutput(self, field):
        """Get the tidied output for a specific field from the request
        if available
        """
        request = self.REQUEST
        tidyAttribute = '%s_tidier_data' % field.getName()
        if isinstance(request, HTTPRequest):
            return request.get(tidyAttribute, None)

    def _notifyOfCopyTo(self, container, op=0):
        """Override this to store a flag when we are copied, to be able
        to discriminate the right thing to do in manage_afterAdd here
        below.
        """
        self._v_renamed = 1
        return ATCTContent._notifyOfCopyTo(self, container, op=op)

    security.declarePrivate('manage_afterAdd')
    def manage_afterAdd(self, item, container):
        """Fix text when created througt webdav
        Guess the right mimetype from the id/data
        """
        ATCTContent.manage_afterAdd(self, item, container)
        field = self.getField('text')

        # hook for mxTidy / isTidyHtmlWithCleanup validator
        tidyOutput = self.getTidyOutput(field)
        if tidyOutput:
            if hasattr(self, '_v_renamed'):
                mimetype = field.getContentType(self)
                del self._v_renamed
            else:
                mimetype = self.guessMimetypeOfText()
            if mimetype:
                field.set(self, tidyOutput, mimetype=mimetype) # set is ok
            elif tidyOutput:
                field.set(self, tidyOutput) # set is ok

    security.declarePrivate('cmf_edit')
    def cmf_edit(self, text_format, text, file='', safety_belt='', **kwargs):
        assert file == '', 'file currently not supported' # XXX
        self.setText(text, mimetype=translateMimetypeAlias(text_format))
        self.update(**kwargs)

    def deferring(self):
        """
        """
        t = time.time()
        time.sleep(10)
        return str(time.time(), t)

    security.declarePrivate('manage_afterPUT')
    def manage_afterPUT(self, data, marshall_data, file, context, mimetype,
                        filename, REQUEST, RESPONSE):
        """After webdav/ftp PUT method

        Set title according to the id on webdav/ftp PUTs.
        """

        if '' == data:
            file.seek(0)
            content = file.read(65536)
        else:
            content = data

        if -1 != content.lower().find("<html>"):
            parser = SimpleHTMLParser()
            parser.feed(content)
            if parser.title:
                self.setTitle(parser.title)
            return

        ATCTContent.manage_afterPUT(self, data, marshall_data, file,
                                    context, mimetype, filename, REQUEST,
                                    RESPONSE)

registerATCT(ATDocument, PROJECTNAME)
