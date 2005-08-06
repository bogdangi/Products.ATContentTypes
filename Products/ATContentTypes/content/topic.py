#  ATContentTypes http://sf.net/projects/collective/
#  Archetypes reimplementation of the CMF core types
#  Copyright (c) 2003-2005 AT Content Types development team
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
__author__  = 'Christian Heimes <ch@comlounge.net>, Alec Mitchell'
__docformat__ = 'restructuredtext'
__old_name__ = 'Products.ATContentTypes.types.ATTopic'

from types import ListType
from types import TupleType
from types import StringType

from Products.CMFCore.permissions import View
from Products.CMFCore.permissions import ModifyPortalContent
from Products.CMFCore.permissions import ManageProperties
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.CatalogTool import CatalogTool
from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from Acquisition import aq_parent
from Acquisition import aq_inner
from zExceptions import NotFound
from webdav.Resource import Resource as WebdavResoure

from Products.Archetypes.public import Schema
from Products.Archetypes.public import BooleanField
from Products.Archetypes.public import IntegerField
from Products.Archetypes.public import LinesField
from Products.Archetypes.public import BooleanWidget
from Products.Archetypes.public import IntegerWidget
from Products.Archetypes.public import InAndOutWidget
from Products.Archetypes.public import DisplayList

from Products.ATContentTypes.config import PROJECTNAME
from Products.ATContentTypes.config import HAS_PLONE2
from Products.ATContentTypes.content.base import registerATCT
from Products.ATContentTypes.content.base import ATCTFolder
from Products.ATContentTypes.content.base import updateActions
from Products.ATContentTypes.criteria import _criterionRegistry
from Products.ATContentTypes.permission import ChangeTopics
from Products.ATContentTypes.permission import AddTopics
from Products.ATContentTypes.content.schemata import ATContentTypeSchema
from Products.ATContentTypes.content.schemata import finalizeATCTSchema
from Products.ATContentTypes.interfaces import IATTopic
from Products.ATContentTypes.interfaces import IATTopicSearchCriterion
from Products.ATContentTypes.interfaces import IATTopicSortCriterion
from Products.ATContentTypes.config import TOOLNAME

from Products.CMFPlone.PloneBatch import Batch

# A couple of fields just don't make sense to sort (for a user),
# some are just doubles.
IGNORED_FIELDS = ['Date', 'allowedRolesAndUsers', 'getId', 'in_reply_to', 
    'meta_type',
    # 'portal_type' # portal type and Type might differ!
    ]

ATTopicSchema = ATContentTypeSchema.copy() + Schema((
    BooleanField('acquireCriteria',
                required=False,
                mode="rw",
                default=False,
                write_permission = ChangeTopics,
                widget=BooleanWidget(
                        label="Inherit Criteria",
                        label_msgid="label_inherit_criteria",
                        description=("Narrow down the search results from the parent Smart Folder(s) "
                                     "by using the criteria from this Smart Folder."),
                        description_msgid="help_inherit_criteria",
                        i18n_domain = "plone",
                        # Only show when the parent object is a Topic also,
                        # for some reason the checkcondition passes the
                        #template as 'object', and the object as 'folder'.
                        condition = "python:folder.getParentNode().portal_type == 'Topic'"),
                ),
    BooleanField('limitNumber',
                required=False,
                mode="rw",
                default=False,
                write_permission = ChangeTopics,
                widget=BooleanWidget(
                        label="Limit Search Results",
                        label_msgid="label_limit_number",
                        description=("If selected, only the 'Number of Items' "
                                     "indicated below will be displayed."),
                        description_msgid="help_limit_number",
                        i18n_domain = "plone"),
                ),
    IntegerField('itemCount',
                required=False,
                mode="rw",
                default=0,
                write_permission = ChangeTopics,
                widget=IntegerWidget(
                        label="Number of Items",
                        label_msgid="label_item_count",
                        description="",
                        description_msgid="help_item_count",
                        i18n_domain = "plone"),
                 ),
    BooleanField('customView',
                required=False,
                mode="rw",
                default=False,
                write_permission = ChangeTopics,
                widget=BooleanWidget(
                        label="Display as Table",
                        label_msgid="label_custom_view",
                        description="Columns in the table are controlled by "
                        "'Table Columns' below.",
                        description_msgid="help_custom_view",
                        i18n_domain = "plone"),
                 ),
    LinesField('customViewFields',
                required=False,
                mode="rw",
                default=('Title',),
                vocabulary='listMetaDataFields',
                enforceVocabulary=True,
                write_permission = ChangeTopics,
                widget=InAndOutWidget(
                        label="Table Columns",
                        label_msgid="label_custom_view_fields",
                        description="Select which fields to display when "
                        "'Display as Table' is checked.",
                        description_msgid="help_custom_view_fields",
                        i18n_domain = "plone"),
                 ),
    ))
finalizeATCTSchema(ATTopicSchema, folderish=True, moveDiscussion=False)


class ATTopic(ATCTFolder):
    """An automatically updated stored search that can be used to display items matching criteria you specify."""

    schema         =  ATTopicSchema

    content_icon   = 'topic_icon.gif'
    meta_type      = 'ATTopic'
    portal_type    = 'Topic'
    archetype_name = 'Smart Folder'
    immediate_view = 'atct_topic_view'
    default_view   = 'atct_topic_view'
    suppl_views    = ()
    _atct_newTypeFor = {'portal_type' : 'CMF Topic', 'meta_type' : 'Portal Topic'}
    typeDescription= 'An automatically updated stored search that can be used to display items matching criteria you specify.'
    typeDescMsgId  = 'description_edit_topic'
    assocMimetypes = ()
    assocFileExt   = ()
    cmf_edit_kws   = ()

    filter_content_types  = 1
    allowed_content_types = ('Topic',)

    use_folder_tabs = 0

    __implements__ = ATCTFolder.__implements__, IATTopic

    security       = ClassSecurityInfo()
    actions = updateActions(ATCTFolder,
        (
        #{
        #'id'          : 'view',
        #'name'        : 'View',
        #'action'      : 'string:${folder_url}/',
        #'permissions' : (View,)
        #},
        {
        'id'          : 'edit',
        'name'        : 'Edit',
        'action'      : 'string:${object_url}/edit',
        'permissions' : (ChangeTopics,)
        },
        {
        'id'          : 'criteria',
        'name'        : 'Criteria',
        'action'      : 'string:${folder_url}/criterion_edit_form',
        'permissions' : (ChangeTopics,)
         },
        {
        'id'          : 'subtopics',
        'name'        : 'Subfolders',
        'action'      : 'string:${folder_url}/atct_topic_subtopics',
        'permissions' : (ChangeTopics,)
        },
       )
    )

    security.declareProtected(ChangeTopics, 'validateAddCriterion')
    def validateAddCriterion(self, indexId, criteriaType):
        """Is criteriaType acceptable criteria for indexId
        """
        return criteriaType in self.criteriaByIndexId(indexId)

    security.declareProtected(ChangeTopics, 'criteriaByIndexId')
    def criteriaByIndexId(self, indexId):
        catalog_tool = getToolByName(self, CatalogTool.id)
        indexObj = catalog_tool.Indexes[indexId]
        results = _criterionRegistry.criteriaByIndex(indexObj.meta_type)
        return results

    security.declareProtected(ChangeTopics, 'listCriteriaTypes')
    def listCriteriaTypes(self):
        """List available criteria types as dict
        """
        return [ {'name': ctype,
                  'description':_criterionRegistry[ctype].shortDesc}
                 for ctype in self.listCriteriaMetaTypes() ]

    security.declareProtected(ChangeTopics, 'listCriteriaMetaTypes')
    def listCriteriaMetaTypes(self):
        """List available criteria
        """
        val = _criterionRegistry.listTypes()
        val.sort()
        return val

    security.declareProtected(ChangeTopics, 'listSearchCriteriaTypes')
    def listSearchCriteriaTypes(self):
        """List available search criteria types as dict
        """
        return [ {'name': ctype,
                  'description':_criterionRegistry[ctype].shortDesc}
                 for ctype in self.listSearchCriteriaMetaTypes() ]

    security.declareProtected(ChangeTopics, 'listSearchCriteriaMetaTypes')
    def listSearchCriteriaMetaTypes(self):
        """List available search criteria
        """
        val = _criterionRegistry.listSearchTypes()
        val.sort()
        return val

    security.declareProtected(ChangeTopics, 'listSortCriteriaTypes')
    def listSortCriteriaTypes(self):
        """List available sort criteria types as dict
        """
        return [ {'name': ctype,
                  'description':_criterionRegistry[ctype].shortDesc}
                 for ctype in self.listSortCriteriaMetaTypes() ]

    security.declareProtected(ChangeTopics, 'listSortCriteriaMetaTypes')
    def listSortCriteriaMetaTypes(self):
        """List available sort criteria
        """
        val = _criterionRegistry.listSortTypes()
        val.sort()
        return val

    security.declareProtected(View, 'listCriteria')
    def listCriteria(self):
        """Return a list of our criteria objects.
        """
        val = self.objectValues(self.listCriteriaMetaTypes())
        # XXX Sorting results in inconsistent order. Leave them in the order
        # they were added.
        #val.sort()
        return val

    security.declareProtected(View, 'listSearchCriteria')
    def listSearchCriteria(self):
        """Return a list of our search criteria objects.
        """
        return [val for val in self.listCriteria() if
             IATTopicSearchCriterion.isImplementedBy(val)]

    security.declareProtected(ChangeTopics, 'hasSortCriterion')
    def hasSortCriterion(self):
        """Tells if a sort criterai is already setup.
        """
        return not self.getSortCriterion() is None

    security.declareProtected(ChangeTopics, 'getSortCriterion')
    def getSortCriterion(self):
        """Return the Sort criterion if setup.
        """
        for criterion in self.listCriteria():
            if IATTopicSortCriterion.isImplementedBy(criterion):
                return criterion
        return None

    security.declareProtected(ChangeTopics, 'removeSortCriterion')
    def removeSortCriterion( self):
        """remove the Sort criterion.
        """
        if self.hasSortCriterion():
            self.deleteCriterion(self.getSortCriterion().getId())

    security.declareProtected(ChangeTopics, 'setSortCriterion')
    def setSortCriterion( self, field, reversed):
        """Set the Sort criterion.
        """
        self.removeSortCriterion()
        self.addCriterion(field, 'ATSortCriterion')
        self.getSortCriterion().setReversed(reversed)

    security.declareProtected(ChangeTopics, 'listIndicesByCriterion')
    def listIndicesByCriterion(self, criterion):
        """
        """
        return _criterionRegistry.indicesByCriterion(criterion)

    security.declareProtected(ChangeTopics, 'listFields')
    def listFields(self):
        """Return a list of fields from portal_catalog.
        """
        tool = getToolByName(self, TOOLNAME)
        return tool.getEnabledFields()

    security.declareProtected(ChangeTopics, 'listSortFields')
    def listSortFields(self):
        """Return a list of available fields for sorting."""
        fields = [ field
                    for field in self.listFields() 
                    if self.validateAddCriterion(field[0], 'ATSortCriterion') ]
        return fields

    security.declareProtected(ChangeTopics, 'listAvailableFields')
    def listAvailableFields(self):
        """Return a list of available fields for new criteria.
        """
        current   = [ crit.Field() for crit in self.listCriteria() ]
        fields = self.listFields()
        val = [ field
                 for field in fields
                 if field[0] not in current
               ]
        return val

    security.declareProtected(View, 'listSubtopics')
    def listSubtopics(self):
        """Return a list of our subtopics.
        """
        val = self.objectValues(self.meta_type)
        check_p = getToolByName(self.portal_membership).checkPermission
        tops = []
        for top in val:
            if check_p('View', top):
                tops.append((top.getTitle().lower(),top))
        tops.sort()
        tops = [t[1] for t in tops]
        return val

    security.declareProtected(View, 'hasSubtopics')
    def hasSubtopics(self):
        """Returns true if subtopics have been created on this topic.
        """
        val = self.objectIds(self.meta_type)
        return not not val

    security.declareProtected(View, 'listMetaDataFields')
    def listMetaDataFields(self, exclude=True):
        """Return a list of metadata fields from portal_catalog.
        """
        tool = getToolByName(self, TOOLNAME)
        return tool.getMetadataDisplay(exclude)

    security.declareProtected(View, 'allowedCriteriaForField')
    def allowedCriteriaForField(self, field, display_list=False):
        """ Return all valid criteria for a given field.  Optionally include
            descriptions in list in format [(desc1, val1) , (desc2, val2)] for
            javascript selector."""
        tool = getToolByName(self, TOOLNAME)
        criteria = tool.getIndex(field).criteria
        allowed = [crit for crit in criteria
                                if self.validateAddCriterion(field, crit)]
        if display_list:
            flat = []
            for a in allowed:
                desc = _criterionRegistry[a].shortDesc
                flat.append((a,desc))
            allowed = DisplayList(flat)
        return allowed

    security.declareProtected(View, 'buildQuery')
    def buildQuery(self):
        """Construct a catalog query using our criterion objects.
        """
        result = {}
        criteria = self.listCriteria()
        acquire = self.getAcquireCriteria()
        if not criteria and not acquire:
            # no criteria found
            return None

        if acquire:
            try:
                # Tracker 290 asks to allow combinations, like this:
                # parent = aq_parent(self)
                parent = aq_parent(aq_inner(self))
                result.update(parent.buildQuery())
            except (AttributeError, Unauthorized): # oh well, can't find parent, or it isn't a Topic.
                pass

        for criterion in criteria:
            for key, value in criterion.getCriteriaItems():
                result[key] = value
        return result

    security.declareProtected(View, 'queryCatalog')
    def queryCatalog(self, REQUEST=None, batch=False, b_size=100,
                                                    full_objects=False, **kw):
        """Invoke the catalog using our criteria to augment any passed
            in query before calling the catalog.
        """
        if REQUEST is None:
            REQUEST = getattr(self, 'REQUEST', {})
        b_start = REQUEST.get('b_start', 0)

        q = self.buildQuery()
        if q is None:
            # empty query - do not show anything
            if batch:
                return Batch([], b_size, int(b_start), orphan=0)
            return []
        # Allow parameters to further limit existing criterias
        for k,v in q.items():
            if kw.has_key(k):
                arg = kw.get(k)
                if isinstance(arg, (ListType,TupleType)) and isinstance(v, (ListType,TupleType)):
                    kw[k] = [x for x in arg if x in v]
                elif isinstance(arg, StringType) and isinstance(v, (ListType,TupleType)) and arg in v:
                    kw[k] = [arg]
                else:
                    kw[k]=v
            else:
                kw[k]=v
        #kw.update(q)
        pcatalog = getToolByName(self, 'portal_catalog')
        limit = self.getLimitNumber()
        max_items = self.getItemCount()
        if limit and self.hasSortCriterion():
            # Sort limit helps Zope 2.6.1+ to do a faster query
            # sorting when sort is involved
            # See: http://zope.org/Members/Caseman/ZCatalog_for_2.6.1
            kw.setdefault('sort_limit', max_items)
        __traceback_info__ = (self, kw,)
        results = pcatalog.searchResults(REQUEST, **kw)
        if full_objects and not limit:
            results = [b.getObject() for b in results]
        if batch:
            batch = Batch(results, b_size, int(b_start), orphan=0)
            return batch
        if limit:
            if full_objects:
                return [b.getObject() for b in results[:max_items]]
            return results[:max_items]
        return results

    security.declareProtected(ChangeTopics, 'addCriterion')
    def addCriterion(self, field, criterion_type):
        """Add a new search criterion. Return the resulting object.
        """
        newid = 'crit__%s_%s' % (field, criterion_type)
        ct    = _criterionRegistry[criterion_type]
        crit  = ct(newid, field)

        self._setObject( newid, crit )
        return self._getOb( newid )

    security.declareProtected(ChangeTopics, 'deleteCriterion')
    def deleteCriterion(self, criterion_id):
        """Delete selected criterion.
        """
        if type(criterion_id) is StringType:
            self._delObject(criterion_id)
        elif type(criterion_id) in (ListType, TupleType):
            for cid in criterion_id:
                self._delObject(cid)

    security.declareProtected(View, 'getCriterion')
    def getCriterion(self, criterion_id):
        """Get the criterion object.
        """
        try:
            return self._getOb('crit__%s' % criterion_id)
        except AttributeError:
            return self._getOb(criterion_id)

    security.declareProtected(AddTopics, 'addSubtopic')
    def addSubtopic(self, id):
        """Add a new subtopic.
        """
        ti = self.getTypeInfo()
        ti.constructInstance(self, id)
        return self._getOb( id )

    security.declarePrivate('synContentValues')
    def synContentValues(self):
        """Getter for syndacation support
        """
        syn_tool = getToolByName(self, 'portal_syndication')
        limit = int(syn_tool.getMaxItems(self))
        brains = self.queryCatalog(sort_limit=limit)[:limit]
        objs = [brain.getObject() for brain in brains]
        return [obj for obj in objs if obj is not None]

    security.declarePublic('canSetDefaultPage')
    def canSetDefaultPage(self):
        """
        Override BrowserDefaultMixin because default page stuff doesn't make
        sense for topics.
        """
        return False

    security.declarePublic('getCriterionUniqueWidgetAttributes')
    def getCriteriaUniqueWidgetAttr(self, attr):
        """Get a unique list values for a specific attribute for all widgets
           on all criteria"""
        criteria = self.listCriteria()
        order = []
        for crit in criteria:
            fields = crit.Schema().fields()
            for f in fields:
                widget = f.widget
                helper = getattr(widget, attr, None)
                # We expect the attribute value to be a iterable.
                if helper:
                    [order.append(item) for item in helper
                        if item not in order]
        return order

    # Beware hack ahead
    security.declarePublic('displayContentsTab')
    def displayContentsTab(self, *args, **kwargs):
        """Only display a contents tab when we are the default page
           because we have our own"""
        putils = getToolByName(self, 'plone_utils', None)
        if putils is not None:
            if putils.isDefaultPage(self):
                script = putils.displayContentsTab.__of__(self)
                return script()
        return False

    def HEAD(self, REQUEST, RESPONSE):
        """Retrieve resource information without a response body.
        
        An empty Topic returns 404 NotFound while a topic w/ a criterion returns
        200 OK.
        """
        self.dav__init(REQUEST, RESPONSE)
        criteria = self.listCriteria()
        acquire = self.getAcquireCriteria()
        if not criteria:
            if not acquire:
                # no criteria found
                raise NotFound, 'The requested resource is empty.'
            else:
                # try to acquire a query
                parent = aq_parent(aq_inner(self))
                try:
                    query = parent.buildQuery()
                except (AttributeError, KeyError):
                    raise NotFound, 'The requested resource is empty.'
                else:
                    if not query:
                        raise NotFound, 'The requested resource is empty.'

        return WebdavResoure.HEAD(self, REQUEST, RESPONSE)

registerATCT(ATTopic, PROJECTNAME)

def modify_fti(fti):
    """Remove folderlisting action
    """
    actions = []
    for action in fti['actions']:
        if action['id'] == 'folderlisting':
                action['visible'] = False

