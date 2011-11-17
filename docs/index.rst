.. Repozitory documentation master file, created by
   sphinx-quickstart on Sat Aug  6 23:16:31 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 2

Introduction
------------

Repozitory is a library for archiving documents and recovering old
versions. It is designed to work in tandem with a primary document
storage mechanism such as ZODB. Repozitory stores the document versions
in a PostgreSQL or SQLite database using SQLAlchemy. Repozitory was
built for KARL, an open source online collaboration system, but
Repozitory is intended to be useful for any Python project that stores
user-editable documents.  Repozitory does not require ZODB.

Using Repozitory, an application can support document versioning
without burdening its own database schema with support for multiple
document versions. Repozitory provides a stable database schema that
rarely needs to change when applications change.

The version control model implemented by Repozitory is designed to be
simple for end users, so it is not as elaborate as version control
systems designed for software developers. In Repozitory, each document
is versioned independently. The attributes of containers are not
normally included in Repozitory, but Repozitory tracks the contents of
containers in order to provide an undelete facility.

Usage
-----

.. py:module:: repozitory.archive

Install Repozitory using Setuptools::

    easy_install repozitory

The main class in Repozitory is :class:`Archive`. Its constructor
requires one parameter, an :class:`EngineParams` object (or any object
that has ``db_string`` and ``kwargs`` attributes). Here is one way
for applications to create an :class:`Archive` instance::

    from repozitory.archive import EngineParams
    from repozitory.archive import Archive

    params = EngineParams('sqlite:///', echo=True)
    archive = Archive(params)

:class:`Archive` objects can be stored in ZODB or any other database
that pickles objects, so if your application is based on ZODB, then you
probably want to store the Archive object as an attribute of some root
object.

Archiving a document
~~~~~~~~~~~~~~~~~~~~

To archive a document, applications call the ``archive`` method of the
Archive, passing an object that provides the :class:`IObjectVersion`
interface. The :class:`IObjectVersion` interface specifies the
following attributes.

- ``docid``
    A unique 32 bit integer document identifier.

- ``title``
    The document title as a Unicode string.  May be left blank.

- ``description``
    The document description as a Unicode string.  May be left blank.

- ``created``
    The :class:`datetime` when the document was created.  Should be in
    UTC, so applications should use ``datetime.datetime.utcnow()``.

- ``modified``
    The :class:`datetime` when the document was last modified.  Should be
    in UTC, so applications should use ``datetime.datetime.utcnow()``.

- ``path``
    The location of the document as a Unicode string, such as
    '/some/path/mydoc'.  May be left blank, but the path improves
    the convenience of the relational database, so applications
    should provide it when possible.

- ``attrs``
    The content and other attributes of the document as a JSON-compatible
    Python dict.  The content of this attribute will be encoded as JSON
    in the relational database.  May be set to None.  It is not
    appropriate to include binary streams in the ``attrs`` attribute;
    store binary streams using ``blobs`` instead.

- ``blobs``
    A mapping of binary large objects to store with this document.
    This attribute allows applications to store images and other
    binary streams of arbitrary size.  May be set to None.

    Each key in the mapping is a Unicode string.  Each value is
    either a filename or an open file object (such as a StringIO).
    Open file objects must be seekable.

    Repozitory automatically de-duplicates binary streams using MD5 and
    SHA-256 hashes, so even if many versions of a document (or many
    documents) use a single large image, Repozitory will store only one
    copy of that image, saving storage space.

- ``user``
    The user who last changed the document, as a Unicode
    string.  Applications should normally store user IDs rather than
    user names in this attribute.

- ``comment``
    The user's comment relating to this version of the document, if any.
    May be None.

- ``klass`` (optional)
    The Python class of the document being stored. Repozitory will
    verify that the class is importable (exists in the scope of some
    module), since importing the class is often useful for recovery
    purposes. If this attribute is not provided, Repozitory will try to
    determine the class automatically.

Repozitory integrates with the :mod:`transaction` package, so the results
of calling ``archive`` will not be committed until you call
``transaction.commit``. Here is an example of how applications might
use the ``archive`` method.

.. testcode::

    from cStringIO import StringIO
    import datetime
    import transaction
    from repozitory.archive import EngineParams
    from repozitory.archive import Archive


    class MyDocument(object):
        def __init__(self, docid, title, description, text, image_data):
            self.docid = docid
            self.title = title
            self.description = description
            self.created = datetime.datetime.utcnow()
            self.text = text
            self.image_data = image_data


    class MyDocumentVersion(object):
        # Implements IObjectVersion
        def __init__(self, doc, user, comment=None):
            # assert isinstance(doc, MyDocument)
            self.docid = doc.docid
            self.title = doc.title
            self.description = doc.description
            self.created = doc.created
            self.modified = datetime.datetime.utcnow()
            self.path = u'/doc/%d' % doc.docid
            self.attrs = {'text': doc.text}
            self.blobs = {'image': StringIO(doc.image_data)}
            self.user = user
            self.comment = comment
            self.klass = object


    d = MyDocument(
        docid=5,
        title=u'The Life of Brain',
        description=(
            u'Brian is born on the original Christmas, in the stable '
            u'next door. He spends his life being mistaken for a messiah.'
        ),
        text=u'blah blah',
        image_data=(
            'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\xff\xff\xff!'
            '\xf9\x04\x01\x00\x00\x01\x00,\x00\x00\x00\x00\x01\x00\x01'
            '\x00\x00\x02\x02D\x01\x00;'
        ),
    )
    params = EngineParams('sqlite:///', echo=False)
    archive = Archive(params)
    archive.archive(MyDocumentVersion(d, '123', 'Test!'))
    d.title = u'The Life of Brian'
    archive.archive(MyDocumentVersion(d, '123', 'Corrected title'))
    transaction.commit()

Again, don't forget to call ``transaction.commit``!  If you are building
a web application with a WSGI pipeline, the best way to call
``transaction.commit`` is to include a WSGI component such as
:mod:`repoze.tm2` in your pipeline.

Reading a document's history
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``history`` method of an :class:`Archive` object provides a
complete list of versions of a particular document. Pass the document's
``docid``. If you want only the current version of the document, add
the parameter ``only_current=True``. The ``history`` method returns
the most recent version first.

Each item in the history list provides the :class:`IObjectVersion`
interface described above, as well as :class:`IObjectHistoryRecord`.
If a document contained blobs, those blobs will be provided in the
history as open file objects.

The attributes provided by :class:`IObjectHistoryRecord` are:

- ``version_num``
    The version number of the document; starts with 1 and increases
    automatically each time the ``archive`` method is called.

- ``derived_from_version``
    The version number this version was based on.  Set to None
    if this is the first version of the document.

    This is normally (version_num - 1), but that changes if users
    revert documents to older versions.

- ``current_version``
    The current version of the document.  Every history record
    has the same value for ``current_version``.

- ``archive_time``
    The :class:`datetime` when the version was archived.

    This attribute is controlled by Repozitory, not by the
    application, so it may be different from the ``modified``
    value.

The following example shows how to read a document's history.

.. doctest::

    >>> h = archive.history(5)
    >>> len(h)
    2
    >>> h[0].title
    u'The Life of Brian'
    >>> h[0].blobs.keys()
    [u'image']
    >>> len(h[0].blobs['image'].read())
    43
    >>> h[0].version_num
    2
    >>> h[0].derived_from_version
    1
    >>> h[0].current_version
    2

Reverting
~~~~~~~~~

To revert a document, the application should call the ``history``
method, select an historical state to revert to, and change the
corresponding document to match the historical state.

Once the document has been reverted, the application should
call the ``reverted`` method of the archive, passing the ``docid``
and the ``version_num`` that the user chose to revert to.  After
calling ``reverted``, it may be a good idea to call ``archive``
again immediately, causing the reverted version to appear at the
top of the version history (but with a new version number).

Continuing the example:

.. doctest::

    >>> h = archive.history(5)
    >>> len(h)
    2
    >>> h[0].title
    u'The Life of Brian'
    >>> h[1].title
    u'The Life of Brain'
    >>> d.title = h[1].title
    >>> archive.reverted(5, h[1].version_num)
    >>> h = archive.history(5, only_current=True)
    >>> len(h)
    1
    >>> h[0].title
    u'The Life of Brain'

Undeleting
~~~~~~~~~~

Repozitory provides a per-container undelete (a.k.a. trash) facility.
To use it, call the ``archive_container`` method after every change to
a document container (where a document container is a folder, wiki, or
other place where documents are stored). Pass a ``container`` object,
which must provide the :class:`IContainerVersion` interface, and a
``user`` string, which identifies the user who made the change. Objects
that provide the :class:`IContainerVersion` interface must have the
following attributes:

- ``container_id``
    The 32 bit integer ID of the container. Distinct from ``docid``,
    but it would be wise to avoid a clash between the ``docid`` and
    ``container_id`` spaces.

- ``path``
    The location of the container as a Unicode string, such as
    '/some/path'. May be left blank, but the path improves the
    convenience of the relational database, so applications should
    provide it when possible.

- ``map``
    The current contents of the container as a mapping of document name
    (a Unicode string) to document ID. May be an empty mapping.

- ``ns_map``
    Additional contents of the container as a mapping where each key is
    a namespace (a non-empty Unicode string) and each value is a
    mapping of document name to document ID. This is useful when the
    container has multiple document namespaces.  May be an empty mapping.

When you call the ``archive_container`` method, Repozitory will
detect changes to the container and make records of any
deletions and undeletions.  Note that ``archive_container`` does not
keep a history; it only updates the record of the current container
contents.  If your application needs to keep a history of the container
itself, use the ``archive`` method and make sure the ``container_id``
and ``docid`` spaces do not clash.

Continuing the example:

.. testcode::

    class MyContainer(object):
        def __init__(self, container_id, contents):
            self.container_id = container_id
            self.contents = contents

        def __getitem__(self, name):
            return self.contents[name]

    class MyContainerVersion(object):
        # Implements IContainerVersion
        def __init__(self, container):
            # assert isinstance(container, MyContainer)
            self.container_id = container.container_id
            self.path = '/container/%d' % container.container_id
            self.map = dict((name, doc.docid)
                for (name, doc) in container.contents.items())
            self.ns_map = {}

    c = MyContainer(6, {'movie': d})
    archive.archive_container(MyContainerVersion(c), '123')
    transaction.commit()

Now let's say the user has deleted the single item from the container.
The application should record the change using ``archive_container``:

.. testcode::

    del c.contents['movie']
    archive.archive_container(MyContainerVersion(c), '123')
    transaction.commit()

The application can use the ``container_contents`` method of the archive
to get the current state of the container and list the documents deleted
from the container.  The ``container_contents`` method returns an object
that provides :class:`IContainerVersion` as well as
:class:`IContainerRecord`, which provides the ``deleted`` attribute.
The ``deleted`` attribute is a list of objects that provide
:class:`IDeletedItem`.

.. doctest::

    >>> cc = archive.container_contents(6)
    >>> cc.container_id
    6
    >>> cc.path
    u'/container/6'
    >>> cc.map
    {}
    >>> cc.ns_map
    {}
    >>> len(cc.deleted)
    1
    >>> cc.deleted[0].docid
    5
    >>> cc.deleted[0].name
    u'movie'
    >>> cc.deleted[0].deleted_by
    u'123'
    >>> cc.deleted[0].deleted_time is not None
    True
    >>> cc.deleted[0].new_container_ids is None
    True

Note that the new_container_ids attribute in the example above is None,
implying the document was deleted, not moved.  Let's move the document
to a new container.

    >>> new_container = MyContainer(7, {'movie': d})
    >>> archive.archive_container(MyContainerVersion(new_container), '123')
    >>> transaction.commit()
    >>> new_cc = archive.container_contents(7)
    >>> new_cc.container_id
    7
    >>> new_cc.map
    {u'movie': 5}
    >>> len(new_cc.deleted)
    0
    >>> cc = archive.container_contents(6)
    >>> cc.container_id
    6
    >>> cc.map
    {}
    >>> len(cc.deleted)
    1
    >>> cc.deleted[0].name
    u'movie'
    >>> cc.deleted[0].new_container_ids
    [7]

The result of the container_contents method now shows that the document
has been moved to container 7.  The application could use this information
to redirect users accessing the document in the old container (from a
bookmark or a stale search result) to the new document location.

The application can also restore the deleted document by
adding it back to the container. In this example, we already have the
document as ``d``, but in order to get the document to restore,
applications normally have to call ``history(docid,
only_current=True)`` and turn the result into a document object.

.. doctest::

    >>> c.contents['movie'] = d
    >>> archive.archive_container(MyContainerVersion(c), '123')
    >>> transaction.commit()
    >>> cc = archive.container_contents(6)
    >>> cc.map
    {u'movie': 5}
    >>> len(cc.deleted)
    0

As shown in the example, Repozitory removes restored documents from
the deleted list.

Interface Documentation
-----------------------

.. py:module:: repozitory.interfaces

IArchive
~~~~~~~~

.. autointerface:: repozitory.interfaces.IArchive
    :members:


IObjectVersion
~~~~~~~~~~~~~~

.. autointerface:: repozitory.interfaces.IObjectVersion
    :members:

IObjectHistoryRecord
~~~~~~~~~~~~~~~~~~~~

.. autointerface:: repozitory.interfaces.IObjectHistoryRecord
    :members:

IContainerVersion
~~~~~~~~~~~~~~~~~

.. autointerface:: repozitory.interfaces.IContainerVersion
    :members:

IContainerRecord
~~~~~~~~~~~~~~~~

.. autointerface:: repozitory.interfaces.IContainerRecord
    :members:

IDeletedItem
~~~~~~~~~~~~

.. autointerface:: repozitory.interfaces.IDeletedItem
    :members:

Comparison with ZopeVersionControl
----------------------------------

Repozitory and the older ZopeVersionControl product perform a similar
function but do it differently. Both serve as an archive of document
versions, but ZopeVersionControl performs its work by copying complete
ZODB objects to and from a ZODB-based archive, while Repozitory expects
the application to translate data when copying data to and from the
archive.

ZopeVersionControl was designed to minimize the amount of code required
to integrate version control into an existing ZODB application, but in
practice, it turned out that debugging applications that use
ZopeVersionControl is often painful. Applications failed to correctly
distinguish between leaf objects and objects with branches, causing
ZopeVersionControl to either version too many objects or not enough.

Repozitory is less ambitious. Repozitory requires more integration code
than ZopeVersionControl requires, but the integration code is likely to
be more straightforward and easier to debug.

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

