import unittest

from app.models import CodeCall, CodeChunk, ChunkType
from app.symbols import build_symbol_index
from app.dependencies import resolve_call, path_to_module


def make_chunk(path, name, line=1):
    return CodeChunk(
        id=f"{path}::function::{name}::{line}",
        path=path,
        language="python",
        type=ChunkType.FUNCTION,
        name=name,
        start_line=line,
        end_line=line + 2,
        content="pass",
    )


class TestModuleResolution(unittest.TestCase):

    def test_module_qualified_call(self):
        caller = make_chunk("main.py", "process")
        utils_save = make_chunk("utils.py", "save")
        db_save = make_chunk("database.py", "save")

        chunks = [caller, utils_save, db_save]

        symbol_index = build_symbol_index(chunks)
        chunk_by_id = {chunk.id: chunk for chunk in chunks}

        imports_by_file = {
            "main.py": {
                "utils": ("utils", None)
            }
        }

        call = CodeCall(
            caller_id=caller.id,
            callee_name="save",
            qualifier="utils",
        )

        result = resolve_call(
            call,
            symbol_index,
            chunk_by_id,
            imports_by_file,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.caller_id, caller.id)
        self.assertEqual(result.callee_id, utils_save.id)

    def test_unimported_module_remains_unresolved(self):
        caller = make_chunk("main.py", "process")
        utils_save = make_chunk("utils.py", "save")

        chunks = [caller, utils_save]

        call = CodeCall(
            caller_id=caller.id,
            callee_name="save",
            qualifier="utils",
        )

        result = resolve_call(
            call,
            build_symbol_index(chunks),
            {chunk.id: chunk for chunk in chunks},
            {"main.py": {}},
        )

        self.assertIsNone(result)

    def test_module_alias(self):
        caller = make_chunk("main.py", "process")
        utils_save = make_chunk("utils.py", "save")

        chunks = [caller, utils_save]

        call = CodeCall(
            caller_id=caller.id,
            callee_name="save",
            qualifier="u",
        )

        result = resolve_call(
            call,
            build_symbol_index(chunks),
            {chunk.id: chunk for chunk in chunks},
            {"main.py": {"u": ("utils", None)}},
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.callee_id, utils_save.id)

    def test_method_style_call_not_guessed(self):
        caller = make_chunk("main.py", "process")
        utils_save = make_chunk("utils.py", "save")

        chunks = [caller, utils_save]

        call = CodeCall(
            caller_id=caller.id,
            callee_name="save",
            qualifier="user",
        )

        result = resolve_call(
            call,
            build_symbol_index(chunks),
            {chunk.id: chunk for chunk in chunks},
            {"main.py": {}},
        )

        self.assertIsNone(result)

    def test_path_to_module_helper_function(self):
        self.assertEqual(
            path_to_module("services/utils.py"),
            "services.utils"
        )


if __name__ == "__main__":
    unittest.main()