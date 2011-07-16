
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.interface import Attribute
from zope.interface import Interface
from zope.dublincore.interfaces import IDCTimes


class IArchive(Interface):
    """A utility that archives objects."""

    def archive(obj, user, comment=None):
        """Add a version to the archive of an object.

        The object does not need to have been in the archive
        previously.  The object must either implement or be adaptable
        to IObjectVersion.

        The user parameter is a string containing the user ID or
        user name who committed the object.  The comment is
        a comment the user typed (if any).

        Returns the new version number.
        """


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

        To detect the class automatically, do not provide this attribute.
        """)


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

    user = Attribute("The user who committed the version.")

    comment = Attribute("The comment attached to the version; may be None.")


class IContainerIdentity(Interface):
    """The ID and path of a container for version control."""

    container_id = Attribute("The container_id of the object as an integer.")

    path = Attribute("The path of the object as a Unicode string.")
