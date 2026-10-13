
import unittest

from app.models import CodeChunk, CodeCall, CodeDependency, ChunkType
from app.symbols import build_symbol_index
from app.dependencies import resolve_call, resolve_unqualified_call


def make_chunk(
    path: str,
    name: str,
    chunk_type: ChunkType = ChunkType.FUNCTION,
    start_line: int = 1,
) -> CodeChunk:
    """
    Create a CodeChunk for dependency resolution tests.

    Args:
        path: File containing the symbol.
        name: Function or qualified method name.
        chunk_type: Type of code chunk.
        start_line: Starting line number.

    Returns:
        A CodeChunk with a unique ID derived from its metadata.
    """
    return CodeChunk(
        id=f"{path}::{chunk_type.value}::{name}::{start_line}",
        path=path,
        language="python",
        type=chunk_type,
        name=name,
        start_line=start_line,
        end_line=start_line + 2,
        content="pass",
    )


class TestUnqualifiedResolution(unittest.TestCase):

    def setUp(self):
        """
        Create a reusable caller for tests.

        Each test may replace this caller when testing
        a different file or a class method.
        """
        self.caller = make_chunk(
            path="main.py",
            name="process",
        )

    def resolve(self, call: CodeCall, chunks: list[CodeChunk]):
        """
        Build indexes and resolve a call using the main dispatcher.

        Args:
            call: The call to resolve.
            chunks: All repository chunks used for the test.

        Returns:
            A CodeDependency or None.
        """
        symbol_index = build_symbol_index(chunks)

        chunk_by_id = {
            chunk.id: chunk
            for chunk in chunks
        }

        return resolve_call(
            call,
            symbol_index,
            chunk_by_id,
        )

    def test_same_file_function_preferred(self):
        """Prefer a same-file function over another file's function."""

        save_a = make_chunk("a.py", "save")
        save_b = make_chunk("main.py", "save")

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        dependency = self.resolve(
            call,
            [self.caller, save_a, save_b],
        )

        self.assertEqual(
            dependency,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=save_b.id,
            ),
        )

    def test_unique_global_function_fallback(self):
        """Resolve a unique function even when it is in another file."""

        save = make_chunk("utils.py", "save")

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        dependency = self.resolve(
            call,
            [self.caller, save],
        )

        self.assertEqual(
            dependency,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=save.id,
            ),
        )

    def test_multiple_global_functions_unresolved(self):
        """Do not guess when multiple functions exist in other files."""

        save_a = make_chunk("a.py", "save")
        save_b = make_chunk("b.py", "save")

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        dependency = self.resolve(
            call,
            [self.caller, save_a, save_b],
        )

        self.assertIsNone(dependency)

    def test_bare_call_does_not_resolve_to_method(self):
        """A bare save() call must not resolve to User.save()."""

        method = make_chunk(
            path="user.py",
            name="User.save",
            chunk_type=ChunkType.METHOD,
        )

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        dependency = self.resolve(
            call,
            [self.caller, method],
        )

        self.assertIsNone(dependency)

    def test_function_preferred_over_same_name_method(self):
        """A bare call should resolve to a function, not a method."""

        function = make_chunk(
            path="main.py",
            name="save",
            chunk_type=ChunkType.FUNCTION,
        )

        method = make_chunk(
            path="main.py",
            name="User.save",
            chunk_type=ChunkType.METHOD,
        )

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        dependency = self.resolve(
            call,
            [self.caller, function, method],
        )

        self.assertEqual(
            dependency,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=function.id,
            ),
        )

    def test_self_method_resolution_unchanged(self):
        """Ensure self.save() still resolves through the existing logic."""

        caller = make_chunk(
            path="user.py",
            name="User.update",
            chunk_type=ChunkType.METHOD,
            start_line=1,
        )

        callee = make_chunk(
            path="user.py",
            name="User.save",
            chunk_type=ChunkType.METHOD,
            start_line=5,
        )

        call = CodeCall(
            caller_id=caller.id,
            callee_name="save",
            qualifier="self",
        )

        dependency = self.resolve(
            call,
            [caller, callee],
        )

        self.assertEqual(
            dependency,
            CodeDependency(
                caller_id=caller.id,
                callee_id=callee.id,
            ),
        )

    def test_multiple_same_file_definitions_unresolved(self):
        """Do not guess when two definitions exist in the same file."""

        save_first = make_chunk(
            path="main.py",
            name="save",
            start_line=1,
        )

        save_second = make_chunk(
            path="main.py",
            name="save",
            start_line=10,
        )

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        dependency = self.resolve(
            call,
            [self.caller, save_first, save_second],
        )

        self.assertIsNone(dependency)


if __name__ == "__main__":
    unittest.main()
