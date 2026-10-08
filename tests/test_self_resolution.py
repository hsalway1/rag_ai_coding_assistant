import unittest

from app.models import CodeCall, CodeChunk, ChunkType
from app.symbols import build_symbol_index
from app.dependencies import resolve_call


class TestSelfResolution(unittest.TestCase):

    def setUp(self):

        self.caller = CodeChunk(
            id="users.py::method::User.update::2",
            path="users.py",
            language="python",
            type=ChunkType.METHOD,
            name="User.update",
            start_line=2,
            end_line=3,
            content="def update(self): self.save()"
        )

        self.user_save = CodeChunk(
            id="users.py::method::User.save::5",
            path="users.py",
            language="python",
            type=ChunkType.METHOD,
            name="User.save",
            start_line=5,
            end_line=6,
            content="def save(self): pass"
        )

        self.database_save = CodeChunk(
            id="database.py::method::Database.save::2",
            path="database.py",
            language="python",
            type=ChunkType.METHOD,
            name="Database.save",
            start_line=2,
            end_line=3,
            content="def save(self): pass"
        )

        chunks = [
            self.caller,
            self.user_save,
            self.database_save
        ]

        self.symbol_index = build_symbol_index(chunks)

        self.chunk_by_id = {
            chunk.id: chunk
            for chunk in chunks
        }

    def test_self_call_resolves_to_correct_class(self):

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier="self"
        )

        dependency = resolve_call(
            call,
            self.symbol_index,
            self.chunk_by_id
        )

        self.assertIsNotNone(dependency)
        self.assertEqual(
            dependency.callee_id,
            self.user_save.id
        )

    def test_nonexistent_method_remains_unresolved(self):

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="delete",
            qualifier="self"
        )

        dependency = resolve_call(
            call,
            self.symbol_index,
            self.chunk_by_id
        )

        self.assertIsNone(dependency)

    def test_unknown_object_is_not_guessed(self):

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier="user"
        )

        dependency = resolve_call(
            call,
            self.symbol_index,
            self.chunk_by_id
        )

        self.assertIsNone(dependency)


if __name__ == "__main__":
    unittest.main()