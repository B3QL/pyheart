from uuid import uuid4


class UniqueIdentifierMixin:
    def __init__(self):
        self._uuid, *_ = str(uuid4()).split('-')

    @property
    def id(self) -> str:
        return str(self._uuid)

    def __hash__(self) -> int:
        return hash(self.__class__) ^ hash(self._uuid)

    def __eq__(self, other: 'UniqueIdentifierMixin') -> bool:
        return self.__class__ == other.__class__ and self.id == other.id
