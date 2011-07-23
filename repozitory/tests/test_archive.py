"""Tests of repozitory.archive"""

from StringIO import StringIO
import datetime
import unittest2 as unittest


class ArchiveTest(unittest.TestCase):

    def setUp(self):
        import transaction
        transaction.abort()
        from repozitory.archive import forget_sessions
        forget_sessions()

    def tearDown(self):
        import transaction
        transaction.abort()
        from repozitory.archive import forget_sessions
        forget_sessions()

    def _class(self):
        from repozitory.archive import Archive
        return Archive

    def _make(self, *args, **kw):
        return self._class()(*args, **kw)

    def _make_default(self):
        from repozitory.archive import EngineParams
        params = EngineParams('sqlite:///')
        return self._make(params)

    def _make_dummy_object_version(self):
        return DummyObjectVersion()

    def test_verifyImplements_IArchive(self):
        from zope.interface.verify import verifyClass
        from repozitory.interfaces import IArchive
        verifyClass(IArchive, self._class())

    def test_verifyProvides_IArchive(self):
        from zope.interface.verify import verifyObject
        from repozitory.interfaces import IArchive
        verifyObject(IArchive, self._make_default())

    def test_query_session_with_empty_database(self):
        from repozitory.schema import ArchivedObject
        archive = self._make_default()
        session = archive.session
        q = session.query(ArchivedObject).count()
        self.assertEqual(q, 0)

    def test_archive_simple_object(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        ver = archive.archive(obj)
        self.assertEqual(ver, 1)

        from repozitory.schema import ArchivedObject
        rows = archive.session.query(ArchivedObject).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].created, datetime.datetime(2011, 4, 6))

        from repozitory.schema import ArchivedClass
        rows = archive.session.query(ArchivedClass).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].module, u'repozitory.tests.test_archive')
        self.assertEqual(rows[0].name, u'DummyObjectVersion')

        from repozitory.schema import ArchivedState
        rows = archive.session.query(ArchivedState).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].path, u'/my/object')
        self.assertEqual(rows[0].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(rows[0].title, u'Cool Object')
        self.assertEqual(rows[0].description, None)
        self.assertEqual(rows[0].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(rows[0].comment, u'I like version control.')

        from repozitory.schema import ArchivedCurrent
        rows = archive.session.query(ArchivedCurrent).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)

        from repozitory.schema import ArchivedBlob
        rows = archive.session.query(ArchivedBlob).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedContainer
        rows = archive.session.query(ArchivedContainer).all()
        self.assertEqual(len(rows), 0)

        from repozitory.schema import ArchivedContainerItem
        rows = archive.session.query(ArchivedContainerItem).all()
        self.assertEqual(len(rows), 0)

    def test_archive_2_revisions_of_simple_object(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        v1 = archive.archive(obj)
        self.assertEqual(v1, 1)

        obj.title = 'New Title!'
        obj.comment = 'I still like version control.'
        v2 = archive.archive(obj)
        self.assertEqual(v2, 2)

        from repozitory.schema import ArchivedObject
        rows = archive.session.query(ArchivedObject).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].created, datetime.datetime(2011, 4, 6))

        from repozitory.schema import ArchivedClass
        rows = archive.session.query(ArchivedClass).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].module, u'repozitory.tests.test_archive')
        self.assertEqual(rows[0].name, u'DummyObjectVersion')

        from repozitory.schema import ArchivedState
        rows = (archive.session.query(ArchivedState)
            .order_by(ArchivedState.version_num)
            .all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].path, u'/my/object')
        self.assertEqual(rows[0].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(rows[0].title, u'Cool Object')
        self.assertEqual(rows[0].description, None)
        self.assertEqual(rows[0].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(rows[0].comment, u'I like version control.')
        self.assertEqual(rows[1].docid, 4)
        self.assertEqual(rows[1].version_num, 2)
        self.assertEqual(rows[1].path, u'/my/object')
        self.assertEqual(rows[1].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(rows[1].title, u'New Title!')
        self.assertEqual(rows[1].description, None)
        self.assertEqual(rows[1].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(rows[1].comment, u'I still like version control.')

        from repozitory.schema import ArchivedCurrent
        rows = archive.session.query(ArchivedCurrent).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 2)

    def test_archive_with_simple_attachment(self):
        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': StringIO('42')}
        archive = self._make_default()
        archive.archive(obj)

        from repozitory.schema import ArchivedBlob
        rows = archive.session.query(ArchivedBlob).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].chunk_count, 1)
        self.assertEqual(rows[0].length, 2)
        self.assertEqual(rows[0].md5,
            'a1d0c6e83f027327d8461063f4ac58a6')
        self.assertEqual(rows[0].sha256,
            '73475cb40a568e8da8a045ced110137e159f890ac4da883b6b17dc651b3a8049')

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].chunk_index, 0)
        self.assertEqual(rows[0].data, '42')

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[0].content_type, None)
        self.assertEqual(rows[0].attrs, None)

    def test_archive_with_complex_attachment(self):
        from zope.interface import implements
        from repozitory.interfaces import IAttachment

        class DummyAttachment(object):
            implements(IAttachment)
            file = StringIO('42')
            content_type = 'text/plain'
            attrs = {'_MACOSX': {'icon': 'apple-ownz-u'}}

        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': DummyAttachment()}
        archive = self._make_default()
        archive.archive(obj)

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[0].content_type, u'text/plain')
        self.assertEqual(rows[0].attrs, {'_MACOSX': {'icon': 'apple-ownz-u'}})

    def test_archive_with_filename_attachment(self):
        import tempfile
        f = tempfile.NamedTemporaryFile()
        f.write('42')
        f.flush()

        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': f.name}
        archive = self._make_default()
        archive.archive(obj)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].chunk_index, 0)
        self.assertEqual(rows[0].data, '42')

        from repozitory.schema import ArchivedAttachment
        rows = archive.session.query(ArchivedAttachment).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[0].content_type, None)
        self.assertEqual(rows[0].attrs, None)

    def test_archive_deduplicates_attachments(self):
        obj = self._make_dummy_object_version()
        obj.attachments = {'readme.txt': StringIO('42')}
        archive = self._make_default()
        archive.archive(obj)
        obj.attachments['readme2.txt'] = StringIO('24.')
        archive.archive(obj)

        from repozitory.schema import ArchivedBlob
        rows = (archive.session.query(ArchivedBlob)
            .order_by(ArchivedBlob.length)
            .all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].length, 2)
        self.assertEqual(rows[1].length, 3)

        from repozitory.schema import ArchivedChunk
        from sqlalchemy import func
        rows = (archive.session.query(ArchivedChunk)
            .order_by(func.length(ArchivedChunk.data))
            .all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].chunk_index, 0)
        self.assertEqual(rows[0].data, '42')
        self.assertEqual(rows[1].chunk_index, 0)
        self.assertEqual(rows[1].data, '24.')

        from repozitory.schema import ArchivedAttachment
        rows = (archive.session.query(ArchivedAttachment)
            .order_by(ArchivedAttachment.version_num, ArchivedAttachment.name)
            .all())
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].docid, 4)
        self.assertEqual(rows[0].version_num, 1)
        self.assertEqual(rows[0].name, 'readme.txt')
        self.assertEqual(rows[1].docid, 4)
        self.assertEqual(rows[1].version_num, 2)
        self.assertEqual(rows[1].name, 'readme.txt')
        self.assertEqual(rows[2].docid, 4)
        self.assertEqual(rows[2].version_num, 2)
        self.assertEqual(rows[2].name, 'readme2.txt')

        # Confirm that rows 0 and 1, which are different versions,
        # refer to the same blob_id.
        self.assertEqual(rows[0].blob_id, rows[1].blob_id)
        # Row 2 refers to a different blob.
        self.assertNotEqual(rows[0].blob_id, rows[2].blob_id)

    def test_archive_object_that_fails_to_adapt_to_IObjectVersion(self):
        archive = self._make_default()
        with self.assertRaises(TypeError):
            archive.archive(object())

    def test_history_without_attachments(self):
        obj = self._make_dummy_object_version()
        obj.comment = 'change 1'
        archive = self._make_default()
        archive.archive(obj)
        obj.title = 'Changed Title'
        obj.description = 'New Description'
        obj.modified = datetime.datetime(2011, 4, 11)
        obj.user = 'mixer upper'
        obj.comment = None
        archive.archive(obj)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)

        self.assertEqual(records[0].docid, 4)
        self.assertEqual(records[0].path, u'/my/object')
        self.assertEqual(records[0].created, datetime.datetime(2011, 4, 6))
        self.assertEqual(records[0].modified, datetime.datetime(2011, 4, 7))
        self.assertEqual(records[0].version_num, 1)
        self.assertEqual(records[0].current_version, 2)
        self.assertEqual(records[0].title, u'Cool Object')
        self.assertEqual(records[0].description, None)
        self.assertEqual(records[0].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(records[0].user, 'tester')
        self.assertEqual(records[0].comment, 'change 1')
        self.assertFalse(records[0].attachments)
        self.assertEqual(records[0].klass, DummyObjectVersion)

        self.assertEqual(records[1].docid, 4)
        self.assertEqual(records[1].path, u'/my/object')
        self.assertEqual(records[1].created, datetime.datetime(2011, 4, 6))
        self.assertEqual(records[1].modified, datetime.datetime(2011, 4, 11))
        self.assertEqual(records[1].version_num, 2)
        self.assertEqual(records[1].current_version, 2)
        self.assertEqual(records[1].title, u'Changed Title')
        self.assertEqual(records[1].description, u'New Description')
        self.assertEqual(records[1].attrs, {'a': 1, 'b': [2]})
        self.assertEqual(records[1].user, 'mixer upper')
        self.assertEqual(records[1].comment, None)
        self.assertFalse(records[1].attachments)
        self.assertEqual(records[1].klass, DummyObjectVersion)

        self.assertGreater(records[0].archive_time, records[0].created)

    def test_history_with_small_attachment(self):
        from zope.interface import implements
        from repozitory.interfaces import IAttachment

        class DummyAttachment(object):
            implements(IAttachment)
            file = StringIO('42')
            content_type = 'text/plain'
            attrs = {'_MACOSX': {'icon': 'apple-ownz-u'}}

        obj = self._make_dummy_object_version()
        archive = self._make_default()
        archive.archive(obj)
        obj.attachments = {'x': DummyAttachment()}
        archive.archive(obj)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 1)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)
        self.assertFalse(records[0].attachments)

        self.assertTrue(records[1].attachments)
        self.assertEqual(records[1].attachments.keys(), ['x'])
        a = records[1].attachments['x']
        self.assertEqual(a.content_type, 'text/plain')
        self.assertEqual(a.attrs, {'_MACOSX': {'icon': 'apple-ownz-u'}})
        self.assertEqual(a.file.read(), '42')

    def test_history_with_large_attachment(self):
        from zope.interface import implements
        from repozitory.interfaces import IAttachment

        class DummyAttachment(object):
            implements(IAttachment)
            file = StringIO('*' * 10485760)  # 10 MiB
            content_type = 'application/octet-stream'

        archive = self._make_default()
        obj = self._make_dummy_object_version()
        obj.attachments = {'x': DummyAttachment()}
        archive.archive(obj)

        from repozitory.schema import ArchivedChunk
        rows = archive.session.query(ArchivedChunk).all()
        self.assertEqual(len(rows), 10)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].attachments.keys(), ['x'])
        a = records[0].attachments['x']
        self.assertEqual(a.content_type, 'application/octet-stream')
        self.assertEqual(a.attrs, None)
        self.assertEqual(len(a.file.read()), 10485760)

    def test_reverted(self):
        obj = self._make_dummy_object_version()
        archive = self._make_default()
        v1 = archive.archive(obj)
        self.assertEqual(v1, 1)

        obj.title = 'New Title!'
        v2 = archive.archive(obj)
        self.assertEqual(v2, 2)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].version_num, 1)
        self.assertEqual(records[1].version_num, 2)
        self.assertEqual(records[0].current_version, 2)
        self.assertEqual(records[1].current_version, 2)

        archive.reverted(obj.docid, 1)

        records = archive.history(obj.docid)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].version_num, 1)
        self.assertEqual(records[1].version_num, 2)
        self.assertEqual(records[0].current_version, 1)
        self.assertEqual(records[1].current_version, 1)


from repozitory.interfaces import IObjectVersion
from zope.interface import implements

class DummyObjectVersion(object):
    implements(IObjectVersion)
    docid = 4
    path = '/my/object'
    created = datetime.datetime(2011, 4, 6)
    modified = datetime.datetime(2011, 4, 7)
    title = 'Cool Object'
    description = None
    attrs = {'a': 1, 'b': [2]}
    user = 'tester'
    comment = 'I like version control.'

