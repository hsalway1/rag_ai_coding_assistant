
import unittest

from app.models import CodeChunk, CodeCall, CodeDependency, ChunkType
from app.symbols import build_symbol_index
from app.dependencies import resolve_call, extract_imports


def make_chunk(
    path: str,
    name: str,
    start_line: int = 1,
) -> CodeChunk:
    """
    Create a top-level function chunk for testing.

    Args:
        path: Repository-relative path to the source file.
        name: Name of the function.
        start_line: Starting line number of the function.

    Returns:
        A CodeChunk representing the function.
    """
    return CodeChunk(
        id=f"{path}::function::{name}::{start_line}",
        path=path,
        language="python",
        type=ChunkType.FUNCTION,
        name=name,
        start_line=start_line,
        end_line=start_line + 2,
        content=f"def {name}():\n    pass",
    )


class TestDirectImportResolution(unittest.TestCase):

    def setUp(self):
        """Create a reusable caller in main.py."""
        self.caller = make_chunk(
            path="main.py",
            name="process",
        )

    def resolve(
        self,
        call: CodeCall,
        chunks: list[CodeChunk],
        source: str,
    ) -> CodeDependency | None:
        """
        Resolve a call using imports extracted from main.py.

        Args:
            call: Function call to resolve.
            chunks: All CodeChunk objects in the repository.
            source: Source code containing import declarations.

        Returns:
            The resolved dependency or None.
        """
        symbol_index = build_symbol_index(chunks)

        chunk_by_id = {
            chunk.id: chunk
            for chunk in chunks
        }

        imports_by_file = {
            "main.py": extract_imports(source)
        }

        return resolve_call(
            call,
            symbol_index,
            chunk_by_id,
            imports_by_file,
        )

    def test_direct_function_import(self):
        """Resolve from utils import save; save()."""

        save = make_chunk("utils.py", "save")

        source = """
from utils import save

def process():
    save()
"""

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller, save],
            source,
        )

        self.assertEqual(
            result,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=save.id,
            ),
        )

    def test_direct_function_alias(self):
        """Resolve from utils import save as persist; persist()."""

        save = make_chunk("utils.py", "save")

        source = """
from utils import save as persist

def process():
    persist()
"""

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="persist",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller, save],
            source,
        )

        self.assertEqual(
            result,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=save.id,
            ),
        )

    def test_import_disambiguates_multiple_functions(self):
        """
        Resolve to the explicitly imported function when
        multiple modules define the same function name.
        """

        utils_save = make_chunk("utils.py", "save")
        database_save = make_chunk("database.py", "save")

        source = """
from utils import save

def process():
    save()
"""

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller, utils_save, database_save],
            source,
        )

        self.assertEqual(
            result,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=utils_save.id,
            ),
        )

    def test_imported_function_missing(self):
        """
        Return None when the imported function is not
        present in the indexed repository.
        """

        source = """
from utils import save

def process():
    save()
"""

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller],
            source,
        )

        self.assertIsNone(result)

    def test_import_does_not_resolve_unrelated_function(self):
        """
        An explicit import from utils must not resolve
        to a function with the same name in database.py.
        """

        database_save = make_chunk("database.py", "save")

        source = """
from utils import save

def process():
    save()
"""

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller, database_save],
            source,
        )

        self.assertIsNone(result)

    def test_alias_does_not_create_original_name_binding(self):
        """
        Importing save as persist does not create an
        import binding for the original name save.

        This case includes no indexed save function so
        repository-wide fallback cannot affect the result.
        """

        source = """
from utils import save as persist

def process():
    save()
"""

        imports = extract_imports(source)

        self.assertIn("persist", imports)
        self.assertNotIn("save", imports)

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller],
            source,
        )

        self.assertIsNone(result)

    def test_no_import_uses_existing_fallback(self):
        """
        Without an explicit import, the existing unique
        repository-wide function fallback should still work.
        """

        save = make_chunk("utils.py", "save")

        source = """
def process():
    save()
"""

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller, save],
            source,
        )

        self.assertEqual(
            result,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=save.id,
            ),
        )

    def test_dotted_module_import(self):
        """
        Resolve a function imported from a dotted module path.
        """

        save = make_chunk("services/utils.py", "save")

        source = """
from services.utils import save

def process():
    save()
"""

        call = CodeCall(
            caller_id=self.caller.id,
            callee_name="save",
            qualifier=None,
        )

        result = self.resolve(
            call,
            [self.caller, save],
            source,
        )

        self.assertEqual(
            result,
            CodeDependency(
                caller_id=self.caller.id,
                callee_id=save.id,
            ),
        )


if __name__ == "__main__":
    unittest.main()
