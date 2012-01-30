
from repozitory.jsontype import JSONType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import deferred
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.schema import ForeignKey
from sqlalchemy.schema import ForeignKeyConstraint
from sqlalchemy.types import BigInteger
from sqlalchemy.types import DateTime
from sqlalchemy.types import Integer
from sqlalchemy.types import LargeBinary
from sqlalchemy.types import String
from sqlalchemy.types import Unicode

Base = declarative_base()


class ArchivedObject(Base):
    """An object in the archive."""
    __tablename__ = 'archived_object'
    docid = Column(BigInteger, primary_key=True, nullable=False,
        autoincrement=False)
    created = Column(DateTime, nullable=False, index=True)


class ArchivedClass(Base):
    """The class of some objects in the archive."""
    __tablename__ = 'archived_class'
    class_id = Column(Integer, nullable=False, primary_key=True)
    module = Column(Unicode, nullable=False, index=True)
    name = Column(Unicode, nullable=False)


class ArchivedState(Base):
    """The state of an object in a particular version.

    Also contains info about the version commit: archive_time, user,
    and comment.
    """
    __tablename__ = 'archived_state'
    docid = Column(BigInteger, ForeignKey('archived_object.docid'),
        primary_key=True, nullable=False)
    version_num = Column(Integer, primary_key=True, nullable=False,
        autoincrement=False)
    derived_from_version = Column(Integer, nullable=True)
    class_id = Column(Integer, ForeignKey('archived_class.class_id'),
        nullable=False, index=True)
    path = Column(Unicode, nullable=False, index=True)
    modified = Column(DateTime, nullable=False, index=True)
    title = Column(Unicode, nullable=True)

    # archive_time is the time in UTC when the version was archived.
    archive_time = Column(DateTime, nullable=False)
    user = Column(Unicode, nullable=False)
    comment = Column(Unicode, nullable=True)

    description = Column(Unicode, nullable=True)
    attrs = Column(JSONType, nullable=True)

    obj = relationship(ArchivedObject)
    class_ = relationship(ArchivedClass, lazy='joined')


class ArchivedCurrent(Base):
    """Reference to the current version of an object."""
    __tablename__ = 'archived_current'
    docid = Column(BigInteger, primary_key=True, nullable=False)
    version_num = Column(Integer, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ['docid', 'version_num'],
            ['archived_state.docid', 'archived_state.version_num'],
        ),
        {},
    )

    state = relationship(ArchivedState)


class ArchivedBlobInfo(Base):
    """Info about a chunked blob.

    This table provides a simple Content Addressable Storage (CAS)
    to save space in the database.
    """
    __tablename__ = 'archived_blob_info'
    blob_id = Column(Integer, primary_key=True, nullable=False)
    chunk_count = Column(Integer, nullable=False)
    length = Column(BigInteger, nullable=False)
    # Blobs are matched by both MD5 and SHA-256.
    md5 = Column(String, nullable=False, index=True)
    sha256 = Column(String, nullable=False)


class ArchivedChunk(Base):
    """A chunk of some blob data."""
    __tablename__ = 'archived_chunk'
    blob_id = Column(Integer, ForeignKey('archived_blob_info.blob_id'),
        primary_key=True, nullable=False, index=True)
    chunk_index = Column(Integer, primary_key=True, nullable=False,
        autoincrement=False)
    chunk_length = Column(Integer, nullable=False)
    data = deferred(Column(LargeBinary, nullable=False))

    blob = relationship(ArchivedBlobInfo,
        backref=backref('chunks', order_by=chunk_index))


class ArchivedBlobLink(Base):
    """A binary file linked to a version of an object."""
    __tablename__ = 'archived_blob_link'
    docid = Column(BigInteger, primary_key=True, nullable=False)
    version_num = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode, primary_key=True, nullable=False)
    blob_id = Column(Integer, ForeignKey('archived_blob_info.blob_id'),
        nullable=True, index=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ['docid', 'version_num'],
            ['archived_state.docid', 'archived_state.version_num'],
        ),
        {},
    )

    state = relationship(ArchivedState, backref='blob_links')
    blob = relationship(ArchivedBlobInfo, lazy='joined')


class ArchivedContainer(Base):
    """A container that has version controlled objects.

    This is not the place to store data about the container itself.
    """
    __tablename__ = 'archived_container'
    container_id = Column(BigInteger, primary_key=True, nullable=False,
        autoincrement=False)
    path = Column(Unicode, nullable=False, index=True)


class ArchivedItem(Base):
    """A version controlled object in a container."""
    __tablename__ = 'archived_item'
    container_id = Column(BigInteger,
        ForeignKey('archived_container.container_id'),
        primary_key=True, index=True, nullable=False)
    namespace = Column(Unicode, primary_key=True, nullable=False,
        default=u'')
    name = Column(Unicode, primary_key=True, nullable=False)
    docid = Column(BigInteger, ForeignKey('archived_object.docid'),
        nullable=False, index=True)

    container = relationship(ArchivedContainer)
    obj = relationship(ArchivedObject)


class ArchivedItemDeleted(Base):
    """An object that has been deleted from a container.

    Does not include items that have been renamed within the container.
    """
    __tablename__ = 'archived_item_deleted'
    container_id = Column(BigInteger,
        ForeignKey('archived_container.container_id'),
        primary_key=True, index=True, nullable=False)
    docid = Column(BigInteger, ForeignKey('archived_object.docid'),
        primary_key=True, nullable=False, index=True)
    namespace = Column(Unicode, nullable=False, default=u'')
    name = Column(Unicode, nullable=False)
    deleted_time = Column(DateTime, nullable=False)
    deleted_by = Column(Unicode, nullable=False)

    container = relationship(ArchivedContainer)
    obj = relationship(ArchivedObject)
