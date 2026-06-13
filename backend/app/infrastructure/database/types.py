import uuid

from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """
    Tipo UUID portable: usa CHAR(36) en SQLite y se puede mapear a
    UUID nativo en PostgreSQL si se desea en el futuro. Almacena/recupera
    siempre como uuid.UUID en Python.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value)
