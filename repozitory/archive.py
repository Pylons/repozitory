
from persistent import Persistent
from repozitory.interfaces import IAttachment
from repozitory.interfaces import IObjectContent
from repozitory.interfaces import IObjectIdentity
from repozitory.schema import ArchivedAttachment
from repozitory.schema import ArchivedBlob
from repozitory.schema import ArchivedBlobPart
from repozitory.schema import ArchivedChunk
from repozitory.schema import ArchivedClass
from repozitory.schema import ArchivedCurrent
from repozitory.schema import ArchivedObject
from repozitory.schema import ArchivedState
from repozitory.schema import Base
from sqlalchemy import func
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import sessionmaker
from zope.component import getAdapter
from zope.sqlalchemy import ZopeTransactionExtension
import hashlib

_sessions = {}  # {db_string: SQLAlchemy session}


class EngineParams(object):
    def __init__(self, db_string, kwargs):
        self.db_string = db_string
        self.kwargs = kwargs


class Archive(Persistent):
    """An object archive that uses SQLAlchemy."""

    _v_session = None
    chunk_size = 1048576

    def __init__(self, engine_params):
        self.engine_params = engine_params

    @property
    def session(self):
        """Get the SQLAlchemy session."""
        session = self._v_session
        if session is None:
            params = self.engine_params
            db_string = params.db_string
            session = _sessions.get(db_string)
            if session is None:
                engine = create_engine(db_string, **params.kwargs)
                session = self._create_session(engine)
            self._v_session = session
        return session

    def _create_session(self, engine):
        Base.metadata.create_all(engine)
        session = scoped_session(sessionmaker(
            extension=ZopeTransactionExtension()))
        session.configure(bind=engine)
        return session

    def archive(self, obj, klass=None):
        """Add a version to the archive of an object.

        The object does not need to have been in the archive
        previously.  The object must either implement or be adaptable
        to IObjectIdentity and IObjectContent.

        Returns the new version number.
        """
        if IObjectIdentity.providedBy(obj):
            obj_id = obj
        else:
            obj_id = getAdapter(obj, IObjectIdentity)
        docid = obj_id.docid

        if IObjectContent.providedBy(obj):
            obj_content = obj
        else:
            obj_content = getAdapter(obj, IObjectContent)

        session = self.session
        prev_version = None
        arc_obj = (session.query(ArchivedObject)
            .filter_by(docid=docid)
            .first())
        if arc_obj is None:
            arc_obj = ArchivedObject(
                docid=docid,
                created=obj_content.created,
            )
            session.add(arc_obj)
        else:
            (prev_version,) = (
                session.query(func.max(ArchivedState.version_num))
                .filter_by(docid=docid)
                .one())

        if klass is None:
            klass = type(obj)
        class_id = self._prepare_class_id(klass)

        arc_state = ArchivedState(
            docid=docid,
            version_num=(prev_version or 0) + 1,
            class_id=class_id,
            path=obj_id.path,
            modified=obj_content.modified,
            title=obj_content.title,
            description=obj_content.description,
            attrs=obj_content.attrs,
        )
        session.add(arc_state)

        attachments = obj_content.attachments
        if attachments:
            for name, value in attachments.items():
                self._attach(arc_state, name, value)

        arc_current = (
            session.query(ArchivedCurrent)
            .filter_by(docid=docid)
            .first())
        if arc_current is None:
            arc_current = ArchivedCurrent(
                docid=docid,
                version_num=arc_state.version_num,
            )
        else:
            arc_current.version_num = arc_state.version_num
        session.flush()
        return arc_state.version_num

    def _prepare_class_id(self, klass):
        """Add a class or reuse an existing class ID."""
        session = self.session
        module = klass.__module__
        name = klass.__name__
        cls = (session.query(ArchivedClass)
            .filter_by(module=module, name=name)
            .first())
        if cls is None:
            cls = ArchivedClass(module=module, name=name)
            session.add(cls)
            session.flush()
        return cls.class_id

    def _attach(self, arc_state, name, value):
        """Add a named attachment to an object state."""
        if IAttachment.providedBy(value):
            content_type = value.content_type
            attrs = value.attrs
            f = value.file
        else:
            content_type = None
            attrs = None
            f = value
        if isinstance(f, basestring):
            fn = f
            f = open(fn, 'rb')
            try:
                blob_id = self._prepare_blob_id(f)
            finally:
                f.close()
        else:
            f.seek(0)
            blob_id = self._prepare_blob_id(f)

        session = self.session
        att = ArchivedAttachment(
            docid=arc_state.docid,
            version_num=arc_state.version_num,
            name=name,
            content_type=content_type,
            blob_id=blob_id,
            attrs=attrs,
        )
        session.add(att)

    def _prepare_blob_id(self, f):
        """Upload a blob or reuse an existing blob with the same data."""
        # Compute the length and hashes of the blob data.
        length = 0
        md5_calc = hashlib.md5()
        sha256_calc = hashlib.sha256()
        while True:
            data = f.read(self.chunk_size)
            if not data:
                break
            length += len(data)
            md5_calc.update(data)
            sha256_calc.update(data)
        md5 = md5_calc.hexdigest()
        sha256 = sha256_calc.hexdigest()
        f.seek(0)

        session = self.session
        arc_blob = (
            session.query(ArchivedBlob)
            .filter_by(length=length, md5=md5, sha256=sha256)
            .first())
        if arc_blob is not None:
            return arc_blob.blob_id

        arc_blob = ArchivedBlob(
            chunk_count=0,
            length=length,
            md5=md5,
            sha256=sha256,
        )
        session.add(arc_blob)
        session.flush()  # Assign arc_blob.blob_id
        blob_id = arc_blob.blob_id

        # Upload the data.
        next_chunk_num = 0
        while True:
            data = f.read(self.chunk_size)
            if not data:
                break
            arc_chunk = ArchivedChunk(data=data)
            del data
            session.add(arc_chunk)
            session.flush()  # Assign arc_chunk.chunk_id
            part = ArchivedBlobPart(
                blob_id=blob_id,
                chunk_num=next_chunk_num,
                chunk_id=arc_chunk.chunk_id,
            )
            session.add(part)
            next_chunk_num += 1

        arc_blob.chunk_count = next_chunk_num
        session.flush()
        return arc_blob.blob_id
