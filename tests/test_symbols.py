import unittest

from app.models import CodeChunk, ChunkType
from app.symbols import build_symbol_index


class TestSymbolIndex(unittest.TestCase):

    def test_indexes_function_by_name(self):
        chunk = CodeChunk(
            id="calculator.py::function::multiply::1",
            path="calculator.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="multiply",
            start_line=1,
            end_line=2,
            content="def multiply(a, b):\n    return a * b"
        )

        symbol_index = build_symbol_index([chunk])

        self.assertIn("multiply", symbol_index)
        self.assertEqual(symbol_index["multiply"], [chunk])

    def test_indexes_method_by_full_and_short_name(self):
        chunk = CodeChunk(
            id="calculator.py::method::Calculator.add::3",
            path="calculator.py",
            language="python",
            type=ChunkType.METHOD,
            name="Calculator.add",
            start_line=3,
            end_line=4,
            content="def add(self, a, b):\n    return a + b"
        )

        symbol_index = build_symbol_index([chunk])

        self.assertIn("Calculator.add", symbol_index)
        self.assertIn("add", symbol_index)

        self.assertEqual(
            symbol_index["Calculator.add"],
            [chunk]
        )

        self.assertEqual(
            symbol_index["add"],
            [chunk]
        )

    def test_preserves_ambiguous_symbols(self):
        first_chunk = CodeChunk(
            id="a.py::function::save::1",
            path="a.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="save",
            start_line=1,
            end_line=2,
            content="def save():\n    pass"
        )

        second_chunk = CodeChunk(
            id="b.py::function::save::1",
            path="b.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="save",
            start_line=1,
            end_line=2,
            content="def save():\n    pass"
        )

        symbol_index = build_symbol_index([
            first_chunk,
            second_chunk
        ])

        self.assertEqual(
            len(symbol_index["save"]),
            2
        )


if __name__ == "__main__":
    unittest.main()