#  ATContentTypes http://sf.net/projects/collective/
#  Archetypes reimplementation of the CMF core types
#  Copyright (c) 2003-2004 AT Content Types development team
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
__author__  = ''
__docformat__ = 'restructuredtext'

from Products.ATContentTypes.config import *

from types import ListType, TupleType, StringType
from locale import strcoll

if HAS_LINGUA_PLONE:
    from Products.LinguaPlone.public import registerType
else:
    from Products.Archetypes.public import registerType

from Products.CMFCore import CMFCorePermissions
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.CatalogTool import CatalogTool
from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent, aq_inner

from Products.ATContentTypes.types.ATContentType import ATCTFolder, updateActions
from Products.ATContentTypes.interfaces.IATTopic import IATTopic
from Products.ATContentTypes.types.criteria import CriterionRegistry
from Products.ATContentTypes.Permissions import ChangeTopics, AddTopics
from Products.ATContentTypes.types.schemata import ATTopicSchema
from Products.ATContentTypes.interfaces.IATTopic import IATTopicSearchCriterion, IATTopicSortCriterion

# A couple of fields just don't make sense to sort (for a user),
# some are just doubles.
IGNORED_FIELDS = ['Date', 'allowedRolesAndUsers', 'getId', 'in_reply_to',
    'meta_type', 'portal_type']

class ATTopic(ATCTFolder):
    """A topic folder"""

    schema         =  ATTopicSchema

    content_icon   = 'topic_icon.gif'
    meta_type      = 'ATTopic'
    archetype_name = 'AT Topic'
    immediate_view = 'atct_topic_view'
    default_view   = 'atct_topic_view'
    suppl_views    = ()
    newTypeFor     = ('Topic', 'Portal Topic')
    typeDescription= ("A topic is a pre-defined search, showing all "
                      "items matching\n criteria you specify. "
                      "Topics may also contain sub-topics.")
    typeDescMsgId  = 'description_edit_topic'
    assocMimetypes = ()
    assocFileExt   = ()
    cmf_edit_kws   = ()

    filter_content_types  = 1
    allowed_content_types = ()

    use_folder_tabs = 0

    __implements__ = ATCTFolder.__implements__, IATTopic

    security       = ClassSecurityInfo()
    actions = updateActions(ATCTFolder,
        (
        {
        'id'          : 'view',
        'name'        : 'View',
        'action'      : 'string:${folder_url}/',
        'permissions' : (CMFCorePermissions.View,)
        },
        {
        'id'          : 'edit',
        'name'        : 'Edit',
        'action'      : 'string:${object_url}/base_edit',
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
        'name'        : 'Subtopics',
        'action'      : 'string:${folder_url}/topic_subtopics_form',
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
        results = CriterionRegistry.criteriaByIndex(indexObj.meta_type)
        return results

    security.declareProtected(ChangeTopics, 'listCriteriaTypes')
    def listCriteriaTypes(self):
        """List available criteria types as dict
        """
        return [ {'name': ctype,
                  'description':CriterionRegistry[ctype].shortDesc}
                 for ctype in self.listCriteriaMetaTypes() ]

    security.declareProtected(ChangeTopics, 'listCriteriaMetaTypes')
    def listCriteriaMetaTypes(self):
        """List available criteria
        """
        val = CriterionRegistry.listTypes()
        val.sort()
        return val

    security.declareProtected(ChangeTopics, 'listSearchCriteriaTypes')
    def listSearchCriteriaTypes(self):
        """List available search criteria types as dict
        """
        return [ {'name': ctype,
                  'description':CriterionRegistry[ctype].shortDesc}
                 for ctype in self.listSearchCriteriaMetaTypes() ]

    security.declareProtected(ChangeTopics, 'listSearchCriteriaMetaTypes')
    def listSearchCriteriaMetaTypes(self):
        """List available search criteria
        """
        val = CriterionRegistry.listSearchTypes()
        val.sort()
        return val

    security.declareProtected(ChangeTopics, 'listSortCriteriaTypes')
    def listSortCriteriaTypes(self):
        """List available sort criteria types as dict
        """
        return [ {'name': ctype,
                  'description':CriterionRegistry[ctype].shortDesc}
                 for ctype in self.listSortCriteriaMetaTypes() ]

    security.declareProtected(ChangeTopics, 'listSortCriteriaMetaTypes')
    def listSortCriteriaMetaTypes(self):
        """List available sort criteria
        """
        val = CriterionRegistry.listSortTypes()
        val.sort()
        return val

    security.declareProtected(ChangeTopics, 'listCriteria')
    def listCriteria(self):
        """Return a list of our criteria objects.
        """
        val = self.objectValues(self.listCriteriaMetaTypes())
        val.sort()
        return val

    security.declareProtected(ChangeTopics, 'listSearchCriteria')
    def listSearchCriteria(self):
        """Return a list of our search criteria objects.
        """
        return [val for val in self.listCriteria() if
             IATTopicSearchCriterion.isImplementedBy(val)]

    security.declareProtected(ChangeTopics, 'hasSortCriteria')
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
        return CriterionRegistry.indicesByCriterion(criterion)

    security.declareProtected(ChangeTopics, 'listFields')
    def listFields(self):
        """Return a list of fields from portal_catalog.
        """
        pcatalog = getToolByName( self, 'portal_catalog' )
        available = pcatalog.indexes()
        val = [ field
                 for field in available
                 if  field not in IGNORED_FIELDS
               ]
        val.sort(lambda x,y: strcoll(self.translate(x),self.translate( y)))
        return val

    security.declareProtected(ChangeTopics, 'listSortFields')
    def listSortFields(self):
        """Return a list of available fields for sorting."""
        fields = [ field
                    for field in self.listFields() 
                    if self.validateAddCriterion(field, 'ATSortCriterion') ]
        return fields

    security.declareProtected(ChangeTopics, 'listAvailableFields')
    def listAvailableFields(self):
        """Return a list of available fields for new criteria.
        """
        current   = [ crit.Field() for crit in self.listCriteria() ]
        val = [ field
                 for field in self.listFields()
                 if field not in current
               ]
        return val

    security.declareProtected(ChangeTopics, 'listSubtopics')
    def listSubtopics(self):
        """Return a list of our subtopics.
        """
        val = self.objectValues(self.meta_type)
        val.sort()
        return val

    security.declareProtected(CMFCorePermissions.View, 'buildQuery')
    def buildQuery(self):
        """Construct a catalog query using our criterion objects.
        """
        result = {}
        criteria = self.listCriteria()
        if not criteria:
            # no criteria found
            return None

        if self.getAcquireCriteria():
            try:
                # Tracker 290 asks to allow combinations, like this:
                # parent = aq_parent(self)
                parent = aq_parent(aq_inner(self))
                result.update(parent.buildQuery())
            except AttributeError: # oh well, can't find parent, or it isn't a Topic.
                pass
            
        for criterion in criteria:
            for key, value in criterion.getCriteriaItems():
                result[key] = value
        return result

    security.declareProtected(CMFCorePermissions.View, 'queryCatalog')
    def queryCatalog(self, REQUEST=None, **kw):
        """Invoke the catalog using our criteria to augment any passed
            in query before calling the catalog.
        """
        q = self.buildQuery()
        if q is None:
            # empty query - do not show anything
            return []
        kw.update(q)
        pcatalog = getToolByName(self, 'portal_catalog')
        limit = self.getLimitNumber()
        max_items = self.getItemCount()
        if limit and self.hasSortCriterion():
            # Sort limit helps Zope 2.6.1+ to do a faster query
            # sorting when sort is involved
            # See: http://zope.org/Members/Caseman/ZCatalog_for_2.6.1
            kw.setdefault('sort_limit', max_items)
        results = pcatalog.searchResults(REQUEST, **kw)
        if limit:
            return results[:max_items]
        return results

    security.declareProtected(ChangeTopics, 'addCriterion')
    def addCriterion(self, field, criterion_type):
        """Add a new search criterion.
        """
        newid = 'crit__%s_%s' % (field, criterion_type)
        ct    = CriterionRegistry[criterion_type]
        crit  = ct(newid, field)

        self._setObject( newid, crit )

    security.declareProtected(ChangeTopics, 'deleteCriterion')
    def deleteCriterion(self, criterion_id):
        """Delete selected criterion.
        """
        if type(criterion_id) is StringType:
            self._delObject(criterion_id)
        elif type(criterion_id) in (ListType, TupleType):
            for cid in criterion_id:
                self._delObject(cid)

    security.declareProtected(CMFCorePermissions.View, 'getCriterion')
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
        limit = syn_tool.getMaxItems(self)
        brains = self.queryCatalog(sort_limit=limit)[:limit]
        return [brain.getObject() for brain in brains]

registerType(ATTopic)

def modify_fti(fti):
    """Remove folderlisting action
    """
    actions = []
    for action in fti['actions']:
        if action['id'] != 'folderlisting':
                actions.append(action)
    fti['actions'] = tuple(actions)
