AT Content Types
================

Installation
------------

Please read INSTALL.txt for a list of requirements before installing this
product. ATContentTypes requires new versions of Python, Zope, Plone and
Archetypes. Make sure you've updated all products.

Reporting bugs / feature requests
---------------------------------

Please use the Plone bug tracker at http://dev.plone.org/plone and use the
Content Types component!

Comparing CMF types with ATContentTypes
---------------------------------------

This is a very rough and short list of differences between the old CMF types
and the new ATContentTypes types.

* Archetypes: All types are written with Archetypes and have all features
  default Archetypes based types have like:

   - autogenerated edit forms based on the schema

   - referenceable

   - Easily enhanceable by subclassing or adding fields to the schema

   - Transformations like restructured text, python source code highlighting,
     pdf to html, office to html and many more.

   - plugable validation of fields

* Clean and documented API.

* Translateable using LinguaPlone.
  
* Dynamic Views: All types are using the new dynamic view FTI that allows you
  to choose the view template per instance. You can configure the templates in
  the portal_types tool. This features is used to turn an ordinary folder into
  a photo album by simple switching to a different view.
  
* Permissions per type and feature: Every type has its own add permission and
  all features like template mixin have their own modify permission, too.

* Numerous small adjustments and enhancements to all types for example:

  - Images can be rotated through the web and have exif informations

  - News Items have an image plus caption

  - Events have a body text

  - Documents have a history tab to show the last changes as an unified diff
    view using the ZODB history.
