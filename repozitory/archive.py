
from cStringIO import StringIO
from repozitory.interfaces import IArchive
from repozitory.interfaces import IContainerRecord
from repozitory.interfaces import IDeletedItem
from repozitory.interfaces import IObjectHistoryRecord
from repozitory.schema import ArchivedBlobInfo
from repozitory.schema import ArchivedBlobLink
from repozitory.schema import ArchivedChunk
from repozitory.schema import ArchivedClass
from repozitory.schema import ArchivedContainer
from repozitory.schema import ArchivedCurrent
from repozitory.schema import ArchivedItem
from repozitory.schema import ArchivedItemDeleted
from repozitory.schema import ArchivedObject
from repozitory.schema import ArchivedState
from repozitory.schema import Base
from sqlalchemy import func
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.session import sessionmaker
from zope.interface import implements
from zope.sqlalchemy import ZopeTransactionExtension
import datetime
import hashlib
import tempfile

_global_sessions = {}  # {db_string: SQLAlchemy session}


def forget_sessions():
    _global_sessions.clear()


class EngineParams(object):
    """Parameters to pass to SQLAlchemy's create_engine() call.

    db_string is an URL such as postgresql://localhost:5432/ .
    The keyword parameters are documented here:

    http://www.sqlalchemy.org/docs/core/engines.html#sqlalchemy.create_engine
    """
    def __init__(self, db_string, **kwargs):
        self.db_string = db_string
        self.kwargs = kwargs


def unicode_or_none(s):
    return unicode(s) if s is not None else None


def find_class(module, name):
    m = __import__(module, None, None, ('__doc__',))
    return getattr(m, name, None)


class Archive(object):
    """An object archive that uses SQLAlchemy.

    Note: instances of this class may be stored in ZODB, so instances
    must only hold things that can be pickled.
    """
    implements(IArchive)

    chunk_size = 1048576    # Store blobs in chunks of this size

    def __init__(self, engine_params):
        self.engine_params = engine_params

    @property
    def session(self):
        """Get the SQLAlchemy session.  Uses a global session pool."""
        params = self.engine_params
        db_string = params.db_string
        session = _global_sessions.get(db_string)
        if session is None:
            engine = create_engine(db_string, **params.kwargs)
            session = self._create_session(engine)
            _global_sessions[db_string] = session
        return session

    def _create_session(self, engine):
        Base.metadata.create_all(engine)
        # Distinguish sessions by thread.
        session = scoped_session(sessionmaker(
            extension=ZopeTransactionExtension()))
        session.configure(bind=engine)
        return session

    def archive(self, obj):
        """Add a version to the archive of an object.

        The object does not need to have been in the archive
        previously.  The object must provide the IObjectVersion interface.

        Returns the new version number.
        """
        docid = obj.docid
        session = self.session
        max_version = None
        arc_obj = (session.query(ArchivedObject)
            .filter_by(docid=docid)
            .first())
        if arc_obj is None:
            arc_obj = ArchivedObject(
                docid=docid,
                created=obj.created,
            )
            session.add(arc_obj)
        else:
            max_version = (
                session.query(func.max(ArchivedState.version_num))
                .filter_by(docid=docid)
                .scalar())

        arc_current = (
            session.query(ArchivedCurrent)
            .filter_by(docid=docid)
            .first())
        if arc_current is None:
            derived_from_version = None
        else:
            derived_from_version = arc_current.version_num

        klass = getattr(obj, 'klass', None)
        if klass is None:
            klass = obj.__class__
        class_id = self._prepare_class_id(klass)

        arc_state = ArchivedState(
            docid=docid,
            version_num=(max_version or 0) + 1,
            derived_from_version=derived_from_version,
            archive_time=datetime.datetime.utcnow(),
            class_id=class_id,
            path=unicode(obj.path),
            modified=obj.modified,
            user=unicode(obj.user),
            title=unicode_or_none(obj.title),
            description=unicode_or_none(obj.description),
            attrs=obj.attrs,
            comment=unicode_or_none(obj.comment),
        )
        session.add(arc_state)

        blobs = getattr(obj, 'blobs', None)
        if blobs:
            for name, value in blobs.items():
                self._link_blob(arc_state, name, value)

        arc_current = (
            session.query(ArchivedCurrent)
            .filter_by(docid=docid)
            .first())
        if arc_current is None:
            arc_current = ArchivedCurrent(
                docid=docid,
                version_num=arc_state.version_num,
            )
            session.add(arc_current)
        else:
            arc_current.version_num = arc_state.version_num
        session.flush()
        return arc_state.version_num

    def _prepare_class_id(self, klass):
        """Add a class or reuse an existing class ID."""
        session = self.session
        module = unicode(klass.__module__)
        name = unicode(klass.__name__)
        actual = find_class(module, name)
        if actual != klass:
            raise TypeError("Broken class reference: %s != %s" % (
                actual, klass))
        cls = (session.query(ArchivedClass)
            .filter_by(module=module, name=name)
            .first())
        if cls is None:
            cls = ArchivedClass(module=module, name=name)
            session.add(cls)
            session.flush()
        return cls.class_id

    def _link_blob(self, arc_state, name, value):
        """Link a named blob to an object state."""
        if isinstance(value, basestring):
            fn = value
            f = open(fn, 'rb')
            try:
                blob_id = self._prepare_blob_id(f)
            finally:
                f.close()
        else:
            f = value
            f.seek(0)
            blob_id = self._prepare_blob_id(f)

        a = ArchivedBlobLink(
            docid=arc_state.docid,
            version_num=arc_state.version_num,
            name=unicode(name),
            blob_id=blob_id,
        )
        arc_state.blob_links.append(a)

    def _prepare_blob_id(self, f):
        """Upload a blob or reuse an existing blob containing the same data."""
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
            session.query(ArchivedBlobInfo)
            .filter_by(length=length, md5=md5, sha256=sha256)
            .first())
        if arc_blob is not None:
            return arc_blob.blob_id

        arc_blob = ArchivedBlobInfo(
            chunk_count=0,
            length=length,
            md5=md5,
            sha256=sha256,
        )
        session.add(arc_blob)
        session.flush()  # Assign arc_blob.blob_id
        blob_id = arc_blob.blob_id

        # Upload the data.
        chunk_index = 0
        while True:
            data = f.read(self.chunk_size)
            if not data:
                break
            arc_chunk = ArchivedChunk(
                blob_id=blob_id,
                chunk_index=chunk_index,
                chunk_length=len(data),
                data=data,
            )
            arc_blob.chunks.append(arc_chunk)
            session.flush()
            chunk_index += 1

        arc_blob.chunk_count = chunk_index
        session.flush()
        return arc_blob.blob_id

    def history(self, docid, only_current=False):
        """Get the history of an object.

        Returns a list of IObjectHistoryRecord.
        The most recent version is listed first.
        """
        created = (self.session.query(ArchivedObject.created)
            .filter_by(docid=docid)
            .scalar())
        current_version = (self.session.query(ArchivedCurrent.version_num)
            .filter_by(docid=docid)
            .scalar())
        q = self.session.query(ArchivedState).filter_by(docid=docid)
        if only_current:
            q = q.filter_by(version_num=current_version)
        rows = q.order_by(ArchivedState.version_num.desc()).all()
        return [ObjectHistoryRecord(row, created, current_version)
            for row in rows]

    def get_version(self, docid, version_num):
        """Return a specific IObjectHistoryRecord for a document.
        """
        created = (self.session.query(ArchivedObject.created)
            .filter_by(docid=docid)
            .scalar())
        current_version = (self.session.query(ArchivedCurrent.version_num)
            .filter_by(docid=docid)
            .scalar())
        row = (self.session.query(ArchivedState)
            .filter_by(docid=docid, version_num=version_num)
            .one())
        return ObjectHistoryRecord(row, created, current_version)

    def reverted(self, docid, version_num):
        """Tell the database that an object has been reverted."""
        session = self.session
        row = session.query(ArchivedCurrent).filter_by(docid=docid).one()
        row.version_num = version_num
        session.flush()

    def archive_container(self, container, user):
        """Update the archive of a container.

        The container parameter must provide the IContainerVersion interface.
        The container does not need to have been in the archive previously.

        Note that this method does not keep a record of container versions.
        It only records the contents of the container and tracks deletions,
        to allow for undeletion of contained objects.

        Returns None.
        """
        container_id = container.container_id
        session = self.session
        now = datetime.datetime.utcnow()
        arc_container = (session.query(ArchivedContainer)
            .filter_by(container_id=container_id)
            .first())
        path = unicode(container.path)
        if arc_container is None:
            arc_container = ArchivedContainer(
                container_id=container_id,
                path=path,
            )
            session.add(arc_container)
            item_list = []
            deleted_list = []
        else:
            if arc_container.path != path:
                arc_container.path = path
            item_list = (session.query(ArchivedItem)
                .filter_by(container_id=container_id)
                .all())
            deleted_list = (session.query(ArchivedItemDeleted)
                .filter_by(container_id=container_id)
                .all())

        old_items = {}  # {(ns, name): ArchivedItem}
        old_docid_names = {}  # {docid: (ns, name)}
        for item in item_list:
            k = (item.namespace, item.name)
            old_items[k] = item
            old_docid_names[item.docid] = k

        new_items = {}  # {(ns, name): docid}
        current_docids = set()
        if container.map:
            for name, docid in container.map.items():
                new_items[(u'', unicode(name))] = docid
                current_docids.add(docid)
        if container.ns_map:
            for ns, m in container.ns_map.items():
                ns = unicode(ns)
                for name, docid in m.items():
                    new_items[(ns, unicode(name))] = docid
                    current_docids.add(docid)

        for k in set(new_items).difference(old_items):
            # Add an item to the container.
            ns, name = k
            docid = new_items[k]
            item = ArchivedItem(
                container_id=container_id,
                namespace=ns,
                name=name,
                docid=docid,
            )
            session.add(item)

        for k in set(old_items).difference(new_items):
            # Remove an item from the container.
            item = old_items[k]
            session.delete(item)

        for k in set(old_items).intersection(new_items):
            item = old_items[k]
            docid = new_items[k]
            if item.docid != docid:
                # An item changed its docid.
                item.docid = docid

        for row in deleted_list:
            if row.docid in current_docids:
                # This item exists, so remove the deletion record.
                session.delete(row)

        for docid in set(old_docid_names).difference(current_docids):
            # At least one item has just been deleted.
            ns, name = old_docid_names[docid]
            row = ArchivedItemDeleted(
                container_id=container_id,
                docid=docid,
                namespace=ns,
                name=name,
                deleted_time=now,
                deleted_by=unicode(user),
            )
            session.add(row)

    def container_contents(self, container_id):
        """Return the contents of a container as IContainerRecord.
        """
        session = self.session
        row = (session.query(ArchivedContainer)
            .filter_by(container_id=container_id)
            .one())
        return ContainerRecord(self, session, row)

    def iter_hierarchy(self, top_container_id, max_depth=None,
            follow_deleted=False, follow_moved=False):
        """Iterate over IContainerRecords in a hierarchy.

        See IArchive.iter_hierarchy for more details.
        """
        session = self.session
        depth = 0
        # to_examine is the list of container_ids to examine at the
        # current depth level.
        to_examine = [top_container_id]
        # 'seen' is a defense against container loops.
        seen = set(to_examine)

        while to_examine:

            # Get all the containers and container contents
            # at this depth level.
            container_rows = (session.query(ArchivedContainer)
                .filter(ArchivedContainer.container_id.in_(to_examine))
                .all())

            combined_item_list = (session.query(ArchivedItem)
                .filter(ArchivedItem.container_id.in_(to_examine))
                .all())

            combined_deleted_rows = (session.query(ArchivedItemDeleted)
                .filter(ArchivedItemDeleted.container_id.in_(to_examine))
                .order_by(
                    ArchivedItemDeleted.deleted_time.desc(),
                    ArchivedItemDeleted.namespace,
                    ArchivedItemDeleted.name)
                .all())

            # Get the map of new container IDs for deleted items at this level.
            new_container_map = {}
            if combined_deleted_rows:
                docids = [row.docid for row in combined_deleted_rows]
                new_container_rows = (
                    session.query(
                        ArchivedItem.docid, ArchivedItem.container_id)
                    .filter(ArchivedItem.docid.in_(docids))
                    .all()
                )
                for docid, container_id in new_container_rows:
                    new_container_map.setdefault(docid, []).append(
                        container_id)

            # Create container records from the data just retrieved.
            for container_row in container_rows:
                container_id = container_row.container_id
                item_list = [item for item in combined_item_list
                    if item.container_id == container_id]
                deleted_rows = [row for row in combined_deleted_rows
                    if row.container_id == container_id]
                record = ContainerRecord(self, session, container_row,
                    item_list, deleted_rows, new_container_map)
                yield record

            # Prepare for the next depth level.
            depth += 1
            if max_depth is not None and depth > max_depth:
                break

            to_examine = []

            for item in combined_item_list:
                docid = item.docid
                if not docid in seen:
                    seen.add(docid)
                    to_examine.append(docid)

            if follow_deleted or follow_moved:
                for row in combined_deleted_rows:
                    docid = row.docid
                    moved = not not new_container_map.get(docid)
                    if ((not moved and follow_deleted) or
                            (moved and follow_moved)):
                        if not docid in seen:
                            seen.add(docid)
                            to_examine.append(docid)

    def filter_container_ids(self, container_ids):
        """Return which of the specified container IDs exist in the archive.
        """
        session = self.session
        rows = (session.query(ArchivedContainer.container_id)
            .filter(ArchivedContainer.container_id.in_(container_ids))
            .all())
        return [container_id for (container_id,) in rows]

    def which_contain_deleted(self, container_ids, max_depth=None):
        """Return the subset of container_ids that have something deleted.
        """
        session = self.session
        depth = 0
        forward = {}  # ancestor_id: set([container_id])
        reverse = {}  # container_id: set([ancestor_id])
        seen = {}     # ancestor_id: set([container_id])
        for container_id in container_ids:
            forward[container_id] = set([container_id])
            reverse[container_id] = set([container_id])
            seen[container_id] = set([container_id])
        res = set()

        while True:
            # Figure out which of the current docids have been deleted.
            to_examine = reverse.keys()
            if not to_examine:
                break
            deleted_rows = (session.query(
                    ArchivedItemDeleted.container_id,
                    ArchivedItemDeleted.docid,
                )
                .filter(ArchivedItemDeleted.container_id.in_(to_examine))
                .all())

            if deleted_rows:
                # Found objects that have been removed from these containers.
                # Now, identify docids that have been moved, not deleted.
                docids = [docid for (_, docid) in deleted_rows]
                moved = set(docid for (docid,) in
                    session.query(ArchivedItem.docid)
                    .filter(ArchivedItem.docid.in_(docids))
                    .all())
                # For each deleted item, add to the list of results
                # and remove from the set of containers to examine further.
                for (container_id, docid) in deleted_rows:
                    if docid not in moved:
                        for ancestor_id in reverse[container_id]:
                            res.add(ancestor_id)
                            forward.pop(ancestor_id, None)
                            seen.pop(ancestor_id, None)

            depth += 1
            if max_depth is not None and depth > max_depth:
                break

            # Move to the next level.
            to_examine = set().union(*forward.values())
            if not to_examine:
                break
            next_forward = {}
            next_reverse = {}
            rows = (session.query(
                    ArchivedItem.container_id, ArchivedItem.docid)
                .filter(ArchivedItem.container_id.in_(to_examine))
                .all())
            for (container_id, docid) in rows:
                for ancestor_id in reverse[container_id]:
                    if docid not in seen[ancestor_id]:
                        seen[ancestor_id].add(docid)
                        fwd_set = next_forward.get(ancestor_id)
                        if fwd_set is None:
                            next_forward[ancestor_id] = fwd_set = set()
                        fwd_set.add(docid)
                        next_reverse.setdefault(docid, set()).add(ancestor_id)
            forward = next_forward
            reverse = next_reverse

        return res


class ObjectHistoryRecord(object):
    implements(IObjectHistoryRecord)

    _blobs = None
    _klass = None

    def __init__(self, state, created, current_version):
        self._state = state
        self.current_version = current_version
        self.derived_from_version = state.derived_from_version
        self.created = created
        self.modified = state.modified
        self.title = state.title
        self.description = state.description
        self.docid = state.docid
        self.path = state.path
        self.attrs = state.attrs or {}
        self.version_num = state.version_num
        self.archive_time = state.archive_time
        self.user = state.user
        self.comment = state.comment

    @property
    def blobs(self):
        blobs = self._blobs
        if blobs is None:
            blobs = {}
            for link in self._state.blob_links:
                blobs[link.name] = BlobReader(link.blob)
            self._blobs = blobs
        return blobs

    @property
    def klass(self):
        res = self._klass
        if res is None:
            cls = self._state.class_
            self._klass = res = find_class(cls.module, cls.name)
        return res


class BlobReader(object):
    """Reads a blob file on demand and delegates to the open file."""

    _file = None
    _max_stringio = 1048576  # If blobs are larger than this, use a temp file.

    def __init__(self, blob):
        self._blob = blob

    def _get_file(self):
        f = self._file
        if f is None:
            length = self._blob.length
            if length <= self._max_stringio:
                # The blob fits in memory.
                f = StringIO()
            else:
                # Write the blob to a temporary file.
                f = tempfile.TemporaryFile()
            for chunk in self._blob.chunks:
                f.write(chunk.data)
            f.seek(0)
            self._file = f
        return f

    def __getattr__(self, name):
        return getattr(self._get_file(), name)

    def write(self, data):
        raise IOError("BlobReader is not writable")

    def writelines(self, data):
        raise IOError("BlobReader is not writable")


class ContainerRecord(object):
    implements(IContainerRecord)

    # Note: this constructor is not part of the documented API.
    def __init__(self, archive, session, row,
            item_list=None, deleted_rows=None, new_container_map=None):
        self._archive = archive
        self.container_id = row.container_id
        self.path = row.path

        self.map = {}
        self.ns_map = {}
        if item_list is None:
            item_list = (session.query(ArchivedItem)
                .filter_by(container_id=self.container_id)
                .all())
        for item in item_list:
            ns = item.namespace
            name = item.name
            if ns:
                m = self.ns_map.get(ns)
                if m is None:
                    self.ns_map[ns] = m = {}
                m[name] = item.docid
            else:
                self.map[name] = item.docid

        self._deleted_rows = deleted_rows
        self._new_container_map = new_container_map

    @property
    def deleted(self):
        session = self._archive.session
        deleted_rows = self._deleted_rows
        if deleted_rows is None:
            deleted_rows = (session.query(ArchivedItemDeleted)
                .filter_by(container_id=self.container_id)
                .order_by(ArchivedItemDeleted.deleted_time.desc(),
                    ArchivedItemDeleted.namespace, ArchivedItemDeleted.name)
                .all())
        new_container_map = self._new_container_map
        if new_container_map is None:
            new_container_map = {}  # {docid: [new_container_id]}
            if deleted_rows:
                # Get the list of new container_ids for all objects
                # deleted from this container.
                docids = [row.docid for row in deleted_rows]
                new_container_rows = (
                    session.query(
                        ArchivedItem.docid, ArchivedItem.container_id)
                    .filter(ArchivedItem.docid.in_(docids))
                    .all()
                )
                for docid, container_id in new_container_rows:
                    new_container_map.setdefault(docid, []).append(
                        container_id)
        return [DeletedItem(row, new_container_map.get(row.docid))
            for row in deleted_rows]


class DeletedItem(object):
    implements(IDeletedItem)

    def __init__(self, row, new_container_ids):
        self.docid = row.docid
        self.namespace = row.namespace
        self.name = row.name
        self.deleted_time = row.deleted_time
        self.deleted_by = row.deleted_by
        self.new_container_ids = new_container_ids
        self.moved = not not new_container_ids
