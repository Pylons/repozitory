.. Repozitory documentation master file, created by
   sphinx-quickstart on Sat Aug  6 23:16:31 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Repozitory Documentation
========================

Introduction
------------

Repozitory is a library for archiving user-edited documents and
recovering old versions. It is designed to work in tandem with a
primary document storage mechanism such as ZODB. Repozitory stores the
document versions in a PostgreSQL or SQLite database using SQLAlchemy.
Repozitory was built for KARL, an open source online collaboration
system, but Repozitory is intended to be useful for any Python project
that stores user-editable documents.

Rationale
---------

Using Repozitory, an application can support document versioning
without burdening its own database schema with support for multiple
document versions. Repozitory provides a stable database schema that
does not need to change when applications change, allowing other
applications to read documents using only the relational database.

Usage
-----

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

Archiving Documents
~~~~~~~~~~~~~~~~~~~

To archive a document, applications call the ``archive`` method of the
Archive, passing an object that provides the :class:`IObjectVersion`
interface.  The :class:`IObjectVersion` interface requires 10
attributes and allows for 1 optional attribute.

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

    Repozitory automatically de-deplicates binary streams using MD5 and
    SHA-256 hashes, so even if many versions of a document (or many
    documents) use the same large image, Repozitory will store only one
    copy of that image, saving storage space.

- ``user``
    The user who last changed the document, as a Unicode
    string.  Applications should normally store user IDs rather than
    user names in this attribute.

- ``comment``
    The user's comment relating to this version of the document, if any.
    May be None.

- ``klass`` (optional)
    The Python class of the document being stored.  Repozitory will
    verify that the class is importable (exists in the scope of some
    module), since importing the class is often useful for recovery
    purposes.  If this attribute is not provided, Repozitory will
    try to determine the class automatically.

Repozitory integrates with the :mod:`transaction` package, so the results
of calling ``archive()`` will not be committed until you call
``transaction.commit()``. Here is an example of how applications might
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

Reading an object's history
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``history()`` method of an :class:`Archive` object provides a
complete list of versions of a particular document. Pass the document's
``docid``. If you want only the current version of the document, add
the parameter ``only_current=True``. The ``history()`` method returns
the most recent version first.

Each item in the history list provides the :class:`IObjectVersion`
interface described above, as well as :class:`IObjectHistoryRecord`.
If a document contained blobs, those blobs will be provided in the
history as open file objects.

The attributes provided by :class:`IObjectHistoryRecord` are:

- ``version_num``
    The version number of the document; starts with 1 and increases
    automatically each time ``archive()`` is called.

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

An example:

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



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

