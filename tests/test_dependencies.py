import unittest

from app.dependencies import resolve_call, resolve_calls
from app.models import (
    CodeCall,
    CodeChunk,
    CodeDependency,
    ChunkType,
)
from app.symbols import build_symbol_index


class TestDependencyResolution(unittest.TestCase):

    def test_resolves_single_candidate(self):
        multiply_chunk = CodeChunk(
            id="calculator.py::function::multiply::1",
            path="calculator.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="multiply",
            start_line=1,
            end_line=2,
            content="def multiply(a, b):\n    return a * b"
        )

        symbol_index = build_symbol_index([multiply_chunk])

        chunk_by_id = {
            multiply_chunk.id: multiply_chunk
        }

        call = CodeCall(
            caller_id="main.py::function::calculate::1",
            callee_name="multiply"
        )

        dependency = resolve_call(
            call,
            symbol_index,
            chunk_by_id
        )

        self.assertIsNotNone(dependency)

        self.assertEqual(
            dependency.caller_id,
            "main.py::function::calculate::1"
        )

        self.assertEqual(
            dependency.callee_id,
            "calculator.py::function::multiply::1"
        )

    def test_returns_none_when_symbol_does_not_exist(self):
        symbol_index = {}
        chunk_by_id = {}

        call = CodeCall(
            caller_id="main.py::function::calculate::1",
            callee_name="print"
        )

        dependency = resolve_call(
            call,
            symbol_index,
            chunk_by_id
        )

        self.assertIsNone(dependency)

    def test_returns_none_when_symbol_is_ambiguous(self):
        first_save = CodeChunk(
            id="a.py::function::save::1",
            path="a.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="save",
            start_line=1,
            end_line=2,
            content="def save():\n    pass"
        )

        second_save = CodeChunk(
            id="b.py::function::save::1",
            path="b.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="save",
            start_line=1,
            end_line=2,
            content="def save():\n    pass"
        )

        chunks = [first_save, second_save]

        symbol_index = build_symbol_index(chunks)

        chunk_by_id = {
            chunk.id: chunk
            for chunk in chunks
        }

        call = CodeCall(
            caller_id="main.py::function::run::1",
            callee_name="save"
        )

        dependency = resolve_call(
            call,
            symbol_index,
            chunk_by_id
        )

        self.assertIsNone(dependency)

    def test_resolve_calls_only_returns_resolved_dependencies(self):
        multiply_chunk = CodeChunk(
            id="calculator.py::function::multiply::1",
            path="calculator.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="multiply",
            start_line=1,
            end_line=2,
            content="def multiply(a, b):\n    return a * b"
        )

        symbol_index = build_symbol_index([multiply_chunk])

        chunk_by_id = {
            multiply_chunk.id: multiply_chunk
        }

        calls = [
            CodeCall(
                caller_id="main.py::function::calculate::1",
                callee_name="multiply"
            ),
            CodeCall(
                caller_id="main.py::function::calculate::1",
                callee_name="print"
            ),
        ]

        dependencies = resolve_calls(
            calls,
            symbol_index,
            chunk_by_id
        )

        self.assertEqual(len(dependencies), 1)

        self.assertEqual(
            dependencies[0].callee_id,
            "calculator.py::function::multiply::1"
        )


if __name__ == "__main__":
    unittest.main()