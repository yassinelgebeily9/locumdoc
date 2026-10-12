"""Runs the main flow tests through FirestoreBackend, with an in-memory stand-in for the Firestore client.

The stand-in copies the behaviour the backend relies on: snapshots with .exists/.to_dict()/.id,
create() refusing an existing id, update() refusing a missing one, and where(filter=FieldFilter).
It checks LocumDoc's Firestore code path end to end without a Google project or network access.
"""
import copy
import os
import random
import string
import unittest
from unittest import mock

from google.api_core.exceptions import AlreadyExists, NotFound

from locumdoc import store
from tests import test_app


class FakeSnapshot:
    def __init__(self, doc_id, data):
        self.id, self._data = doc_id, data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return copy.deepcopy(self._data) if self._data is not None else None


class FakeDocument:
    def __init__(self, coll, doc_id):
        self.coll, self.id = coll, doc_id

    def get(self):
        return FakeSnapshot(self.id, self.coll.docs.get(self.id))

    def set(self, data):
        self.coll.docs[self.id] = copy.deepcopy(data)

    def create(self, data):
        if self.id in self.coll.docs:
            raise AlreadyExists("exists")
        self.set(data)

    def update(self, fields):
        if self.id not in self.coll.docs:
            raise NotFound("missing")
        self.coll.docs[self.id].update(copy.deepcopy(fields))

    def delete(self):
        self.coll.docs.pop(self.id, None)


class FakeQuery:
    def __init__(self, coll, filters=()):
        self.coll, self.filters = coll, list(filters)

    def where(self, *args, filter=None):
        assert filter is not None and not args, "use where(filter=FieldFilter(...))"
        assert filter.op_string == "==", filter.op_string
        return FakeQuery(self.coll, self.filters + [(filter.field_path, filter.value)])

    def stream(self):
        for doc_id, d in list(self.coll.docs.items()):
            if all(d.get(k) == v for k, v in self.filters):
                yield FakeSnapshot(doc_id, d)


class FakeCollection(FakeQuery):
    def __init__(self):
        self.docs = {}
        super().__init__(self)

    def document(self, doc_id=None):
        doc_id = doc_id or "".join(random.choice(string.ascii_letters + string.digits) for _ in range(20))
        return FakeDocument(self, doc_id)


class FakeClient:
    def __init__(self):
        self.colls = {}

    def collection(self, name):
        return self.colls.setdefault(name, FakeCollection())


def fake_backend(_config):
    b = store.FirestoreBackend("test-project")
    b._client, b._pid = FakeClient(), os.getpid()
    return b


class FirestoreMixin:
    def setUp(self):
        patcher = mock.patch.object(store, "backend_from_config", fake_backend)
        patcher.start()
        self.addCleanup(patcher.stop)
        super().setUp()
        assert isinstance(self.app.extensions["store"], store.FirestoreBackend)


class FirestoreFlowTests(FirestoreMixin, test_app.FlowTests):
    pass


class FirestorePublicTests(FirestoreMixin, test_app.PublicTests):
    pass


class FirestoreGradeTests(FirestoreMixin, test_app.GradeTests):
    pass


if __name__ == "__main__":
    unittest.main()
