
"""Abstract base classes for repozitory"""

from abc import ABCMeta
from abc import abstractmethod


class ArchiveInterface(object):
    """A utility that archives objects."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def archive(self, obj):
        """Add a version to the archive of an object.

        The object must provide the ObjectVersion interface.
        The object does not need to have been in the archive previously.  

        Returns the new version number.
        """

    @abstractmethod
    def history(self, docid):
        """Get the history of an object.

        Returns a list of ObjectHistoryRecords.
        The most recent version is listed first.
        """

    @abstractmethod
    def reverted(self, docid, version_num):
        """Tell the database that an object has been reverted."""


class ObjectVersion(object):
    """Provides the versionable content of an object.

    Required attributes:
    
    - docid
        The identity of the object as an integer.

    - path
        The path of the object as a Unicode string.

    - title
        A string containing the object's title.

    - description
        A string containing the object's description.

    - created
        The date and time that the object was created.
    
    - modified
        The date and time the object was last modified in a meaningful way.

    - attrs
        Other attributes as a JSON-encodeable dictionary.

    - user
        The user who made the change. (A string.)

    - comment
        The comment attached to the version; may be None.

    Optional attributes:

    - attachments
        A map of attachments to this object version.  May be None.

        Each key is a unicode string.  Each value is either a
        filename, an open file object (such as a StringIO), or an
        object that provides the Attachment interface.

    - klass
        The class of the object.

        To detect the class automatically, do not set this attribute
        or set it to None.
    """
    __metaclass__ = ABCMeta


class Attachment(object):
    """The metadata and content of a versioned attachment.

    Required attributes:

    - file
        Either a filename or an open file containing the attachment.

    Optional attributes:

    - content_type
        A MIME type string such as 'text/plain'.  May be None.

    - attrs
        Attributes to store as a JSON-encodeable dictionary.  May be None.

    """
    __metaclass__ = ABCMeta


class ObjectHistoryRecord(ObjectVersion):
    """An historical record of an object version.

    Instances will have at least the following attributes:

    - version_num
        The version number of the object; starts with 1.

    - current_version
        The current version number of the object.

    - archive_time
        The datetime in UTC when the version was archived.

        May be different from the modified timestamp if the archive was
        created some time after the object was last modified.

    """
    __metaclass__ = ABCMeta
