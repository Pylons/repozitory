
from zope.interface import Attribute
from zope.interface import Interface

try:  # pragma: no cover
    from zope.dublincore.interfaces import IDCDescriptiveProperties
    from zope.dublincore.interfaces import IDCTimes
except ImportError:    
    # We don't really need to depend on the bulky zope.dublincore
    # package.  Here is a copy of the interfaces we are interested in.
    from zope.schema import Datetime
    from zope.schema import Text
    from zope.schema import TextLine

    class IDCDescriptiveProperties(Interface):
        """Basic descriptive meta-data properties
        """
    
        title = TextLine(
            title = u'Title',
            description =
            u"The first unqualified Dublin Core 'Title' element value."
            )
    
        description = Text(
            title = u'Description',
            description =
            u"The first unqualified Dublin Core 'Description' element value.",
            )
    
    class IDCTimes(Interface):
        """Time properties
        """
    
        created = Datetime(
            title = u'Creation Date',
            description =
            u"The date and time that an object is created. "
            u"\nThis is normally set automatically."
            )
    
        modified = Datetime(
            title = u'Modification Date',
            description =
            u"The date and time that the object was last modified in a\n"
            u"meaningful way."
            )


class IArchive(Interface):
    """A utility that archives objects."""

    def archive(obj):
        """Add a version to the archive of an object.

        The object must either implement or be adaptable to IObjectVersion.
        The object does not need to have been in the archive previously.  

        Returns the new version number.
        """

    def history(docid):
        """Get the history of an object.

        Returns a list of IObjectHistoryRecord.
        The most recent version is listed first.
        """

    def reverted(docid, version_num):
        """Tell the database that an object has been reverted."""


class IObjectVersion(IDCDescriptiveProperties, IDCTimes):
    """The content of an object for version control.

    Note that the following attributes are required, as specified by
    the base interfaces:
    
        title
        description
        created
        modified

    The title and description should be unicode.
    """

    docid = Attribute("The docid of the object as an integer.")

    path = Attribute("The path of the object as a Unicode string.")

    attrs = Attribute(
        """The attributes to store as a JSON-encodeable dictionary.

        May be None.
        """)

    attachments = Attribute(
        """A map of attachments to include.  May be None.

        Each key is a unicode string.  Each value is either a
        filename, an open file object (such as a StringIO), or an
        object that provides IAttachment.
        """)

    klass = Attribute(
        """Optional: the class of the object.

        To detect the class automatically, do not provide this attribute
        or set it to None.
        """)

    user = Attribute("The user who made the change.")

    comment = Attribute("The comment attached to the version; may be None.")


class IAttachment(Interface):
    """The metadata and content of a versioned attachment."""

    file = Attribute(
        "Either a filename or an open file containing the attachment.")

    content_type = Attribute(
        "Optional: A MIME type string such as 'text/plain'")

    attrs = Attribute(
        "Optional: attributes to store as a JSON-encodeable dictionary.")


class IObjectHistoryRecord(IObjectVersion):
    """An historical record of an object version.
    """

    version_num = Attribute("The version number of the object; starts with 1.")

    current_version = Attribute("The current version number of the object.")

    archive_time = Attribute(
        """The datetime in UTC when the version was archived.

        May be different from object.modified.  When in doubt, use
        object.modified rather than archive_time.
        """)


class IContainerIdentity(Interface):
    """The ID and path of a container for version control."""

    container_id = Attribute("The container_id of the object as an integer.")

    path = Attribute("The path of the object as a Unicode string.")
