
from zope.dublincore.interfaces import IDCDescriptiveProperties
from zope.interface import Attribute
from zope.interface import Interface
from zope.dublincore.interfaces import IDCTimes


class IObjectIdentity(Interface):
    """The docid and path of an object for version control."""
    docid = Attribute("The docid of the object as an integer.")
    path = Attribute("The path of the object as a Unicode string.")


class IObjectContent(IDCDescriptiveProperties, IDCTimes):
    """The content of an object for version control.

    Note that the following attributes are required, as specified by
    the base interfaces:
    
        title
        description
        created
        modified
    """

    attrs = Attribute(
        """The attributes to store as a JSON-encodable dictionary.

        May be None.""")

    attachments = Attribute(
        """A map of attachments to include.  May be None.

        Each key is a unicode string and each value is a
        filename, open file object (such as a StringIO), or an
        object that provides IAttachment.
        """)


class IAttachment(Interface):
    """The metadata and content of a versioned attachment."""

    file = Attribute(
        "Either a filename or an open file containing the attachment.")

    content_type = Attribute(
        "Optional: A MIME type string such as 'text/plain'")

    attrs = Attribute(
        "Optional: attributes to store as a JSON-encodable dictionary.")


class IContainerIdentity(Interface):
    """The ID and path of a container for version control."""
    container_id = Attribute("The container_id of the object as an integer.")
    path = Attribute("The path of the object as a Unicode string.")
