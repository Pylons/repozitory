
from sqlalchemy.types import TypeDecorator
from sqlalchemy.types import UnicodeText
import simplejson as json


class JSONType(TypeDecorator):
    """Holds a JSON-serialized object.

    JSONType builds upon the UnicodeText type to apply Python's
    ``json.dumps()`` to incoming objects, and ``json.loads()`` on
    the way out, allowing any JSON compatible object to be stored as
    a Unicode text field.

    Note: This column type is immutable, meaning SQLAlchemy
    will not notice if something changes the content of values
    read from columns of this type.  Values should be replaced only.
    """

    impl = UnicodeText

    def bind_processor(self, dialect):
        impl_processor = self.impl.bind_processor(dialect)
        use_impl_processor = bool(impl_processor)

        def process(value):
            if value is not None:
                value = json.dumps(value, separators=(',', ':'))
                if not isinstance(value, unicode):
                    value = unicode(value, 'ascii')
            if use_impl_processor:
                value = impl_processor(value)
            return value

        return process

    def result_processor(self, dialect, coltype):
        impl_processor = self.impl.result_processor(dialect, coltype)
        use_impl_processor = bool(impl_processor)

        def process(value):
            if use_impl_processor:
                value = impl_processor(value)  # pragma: no cover
            if value:
                value = json.loads(value)
            else:
                value = None
            return value

        return process
