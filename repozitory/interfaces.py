
from zope.interface import Attribute
from zope.interface import Interface

try:  # pragma: no cover
    from zope.dublincore.interfaces import IDCDescriptiveProperties
    from zope.dublincore.interfaces import IDCTimes
except ImportError:
    # We don't really need to depend on the bulky zope.dublincore
    # package if it's not installed.  This is a copy of the interfaces
    # we are interested in.
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

        The obj parameter must provide the IObjectVersion interface.
        The object does not need to have been in the archive previously.

        Returns the new version number.
        """

    def history(docid, only_current=False):
        """Get the history of an object.

        Returns a list of objects that provide IObjectHistoryRecord.
        The most recent version number is listed first.

        If only_current is true, only the current history record
        is returned in the list.  (The most current history record
        might not be the most recent version number if the object
        has been reverted.)
        """

    def get_version(docid, version_num):
        """Return a specific IObjectHistoryRecord for a document.
        """

    def reverted(docid, version_num):
        """Tell the database that an object has been reverted."""

    def archive_container(container, user):
        """Update the archive of a container.

        The container parameter must provide the IContainerVersion interface.
        The container does not need to have been in the archive previously.
        The user parameter (a string) specifies who made the change.

        Note that this method does not keep a record of container versions.
        It only records the contents of the container and tracks deletions,
        to allow for undeletion of contained objects.

        Returns None.
        """

    def container_contents(container_id):
        """Returns the contents of a container as IContainerRecord.
        """

    def iter_hierarchy(top_container_id, max_depth=None,
            follow_deleted=False, follow_moved=False):
        """Iterate over IContainerRecords in a hierarchy.

        This is more efficient than traversing the hierarchy
        by calling the container_contents method repeatedly, because
        this method minimizes the number of calls to the database.
        Yields an IContainerRecord for each container in the
        hierarchy.

        Set the max_depth parameter to limit the depth of containers
        to include. When max_depth is 0, only the top container is included;
        when depth is 1, its children are included, and so on.
        Set max_depth to None (the default) to include containers
        of arbitrary depth.

        If follow_deleted is true, this method will also include
        deleted containers and descendants of deleted containers
        in the results.

        If follow_moved is true, this method will also include
        moved containers and descendants of moved containers
        in the results.

        If no container exists by the given top_container_id, this
        method returns an empty mapping.

        NB: This method assumes that container_ids are also docids.
        (Most other methods make no such assumption.)
        """

    def filter_container_ids(container_ids):
        """Returns which of the specified container IDs exist in the archive.

        Returns a sequence containing a subset of the provided container_ids.
        """

    def which_contain_deleted(container_ids, max_depth=None):
        """Returns the subset of container_ids that have had something deleted.

        This is useful for building a hierarchical trash UI that allows
        users to visit only containers that have had something deleted.
        All descendant containers are examined (unless max_depth limits
        the search.)

        Returns a sequence containing a subset of the provided container_ids.

        NB: This method assumes that container_ids are also docids.
        (Most other methods make no such assumption.)
        """

    def shred(docids=(), container_ids=()):
        """Delete the specified objects and containers permanently.

        The containers to shred must not contain any objects (exempting the
        objects to be shredded), or a ValueError will be raised.

        Returns None.
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

    path = Attribute(
        """The path of the object as a Unicode string.

        Used only as metadata.  May be left empty.
        """)

    attrs = Attribute(
        """The attributes to store as a JSON-encodeable dictionary.

        May be None.
        """)

    blobs = Attribute(
        """A map of binary large objects linked to this state.  May be None.

        Each key is a unicode string.  Each value is either a
        filename or an open file object (such as a StringIO).
        Open file objects must be seekable.
        """)

    klass = Attribute(
        """Optional: the class of the object.

        To detect the class automatically, do not provide this attribute,
        or set it to None.
        """)

    user = Attribute("The user who made the change. (A string)")

    comment = Attribute("The comment linked to the version; may be None.")


class IObjectHistoryRecord(IObjectVersion):
    """An historical record of an object version.

    The IArchive.history() method returns objects that provide this
    interface.  All blobs returned by the history() method are open
    files (not filenames).
    """

    version_num = Attribute("The version number of the object; starts with 1.")

    derived_from_version = Attribute(
        """The version number this version was based on.

        None if the object was created in this version.
        """)

    current_version = Attribute("The current version number of the object.")

    archive_time = Attribute(
        """The datetime in UTC when the version was archived.

        May be different from the modified attribute.  The modified
        attribute is set by the application, whereas the archive_time
        attribute is set by repozitory automatically.
        """)


class IContainerVersion(Interface):
    """The contents of a container for version control."""

    container_id = Attribute("The ID of the container as an integer.")

    path = Attribute(
        """The path of the container as a Unicode string.

        Used only as metadata.  May be left empty.
        """)

    map = Attribute(
        """The current items in the container, as {name: docid}.

        All names must be non-empty strings and all referenced objects
        must already exist in the archive.
        """)

    ns_map = Attribute(
        """Namespaced container items, as {ns: {name: docid}}.

        All namespaces and names must be non-empty strings and all referenced
        objects must already exist in the archive.
        """)


class IContainerRecord(IContainerVersion):
    """Provides the current and deleted contents of a container."""

    deleted = Attribute(
        """The deleted items in the container as a list of IDeletedItem.

        The most recently deleted items are listed first.

        A item name may appear more than once in the list if it has referred
        to different docids at different times.  A docid will never appear
        more than once in the list, since adding an object to a container
        causes the corresponding docid to be removed from the deleted list
        for that container.
        """)


class IDeletedItem(Interface):
    """A record of an item deleted from a container."""

    docid = Attribute("The docid of the deleted object as an integer.")

    namespace = Attribute("""The object's former namespace in the container.

    Empty if the object was not in a namespace.
    """)

    name = Attribute("The object's former name within the container.")

    deleted_time = Attribute("When the object was deleted (a UTC datetime).")

    deleted_by = Attribute("Who deleted the object (a string).")

    new_container_ids = Attribute("""Container(s) where the object now exists.

    Empty or None if the object is not currently in any container.
    """)

    moved = Attribute("""True if this item was moved rather than deleted.

    True when new_container_ids is non-empty.
    """)
