
import ast
import textwrap

from app.models import CodeChunk, CodeCall, ChunkType, CodeDependency


def get_function_calls(node, caller_id: str) -> list[CodeCall]:
    """
    Extract function and method calls from an AST subtree.

    Parameters
    ----------
    node : ast.AST
        The AST node representing the function or method we are analyzing.

        Usually an ast.FunctionDef or ast.AsyncFunctionDef.

        ast.walk(node) recursively visits all descendant AST nodes.

    caller_id : str
        Unique ID of the CodeChunk containing these calls.

        Format:
            "path::type::name::start_line"

        Example:
            "users.py::method::User.update::5"

    Returns
    -------
    list[CodeCall]
        A list containing one CodeCall for each supported call expression.

        Each CodeCall contains:
            caller_id   : ID of the calling CodeChunk
            callee_name : Name of the called function/method
            qualifier   : Expression prefix, or None

        Example:
            For:
                save()
                self.update()

            Returns:
                [
                    CodeCall(caller_id, "save", None),
                    CodeCall(caller_id, "update", "self")
                ]

        Returns [] if no supported calls are found.

    Notes
    -----
    - Only ast.Call nodes are processed.
    - get_call_name() extracts the callee name and qualifier.
    - Nested functions are also traversed by ast.walk().
    - This function extracts syntax; it does not resolve dependencies.
    """
    calls = []

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue

        result = get_call_name(child.func)

        if result is None:
            continue

        callee_name, qualifier = result

        calls.append(
            CodeCall(
                caller_id=caller_id,
                callee_name=callee_name,
                qualifier=qualifier
            )
        )

    return calls


def extract_chunk_calls(chunk: CodeChunk) -> list[CodeCall]:
    """
    Extract raw calls from a function or method CodeChunk.

    Parameters
    ----------
    chunk : CodeChunk
        The repository chunk whose source code we want to analyze.

        Important fields:
            chunk.id      : Unique identifier
            chunk.type    : FUNCTION, METHOD, or CLASS
            chunk.content : Original source code

    Returns
    -------
    list[CodeCall]
        Raw call expressions found inside the chunk.

        Example:
            Given a chunk containing:

                def calculate(a, b):
                    return math_utils.multiply(a, b)

            Returns:
                [
                    CodeCall(
                        caller_id=chunk.id,
                        callee_name="multiply",
                        qualifier="math_utils"
                    )
                ]

        Returns [] when:
            - The chunk is not a FUNCTION or METHOD.
            - The source has a SyntaxError.
            - No supported calls are found.

    Processing
    ----------
    1. Ignore CLASS chunks to avoid duplicating method calls.
    2. Dedent the source so methods can be parsed independently.
    3. Parse the source into an AST.
    4. Find top-level function definitions in the parsed chunk.
    5. Extract calls using get_function_calls().

    Notes
    -----
    CodeCall objects remain unresolved at this stage.
    """
    if chunk.type not in {
        ChunkType.FUNCTION,
        ChunkType.METHOD,
    }:
        return []

    content = textwrap.dedent(chunk.content)

    try:
        tree = ast.parse(content)
    except SyntaxError:
        print("Syntax error!")
        return []

    calls = []

    for node in tree.body:
        if not isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue

        # get_function_calls already returns CodeCall objects.
        calls.extend(get_function_calls(node, chunk.id))

    return calls


def get_call_name(
    func: ast.expr
) -> tuple[str, str | None] | None:
    """
    Extract a callee name and qualifier from an AST call expression.

    Parameters
    ----------
    func : ast.expr
        The expression stored in an ast.Call node's `func` field.

        Examples:
            save()                 -> ast.Name
            self.save()            -> ast.Attribute
            database.user.save()   -> nested ast.Attribute

    Returns
    -------
    tuple[str, str | None] | None
        A tuple in the format:

            (callee_name, qualifier)

        callee_name : str
            Final function or method name.

        qualifier : str | None
            Expression preceding the final name.

        Examples:
            save()
                -> ("save", None)

            self.save()
                -> ("save", "self")

            database.user.save()
                -> ("save", "database.user")

        Returns None for unsupported expressions such as:
            get_user().save()

    Processing
    ----------
    For ast.Name:
        Return its identifier directly.

    For ast.Attribute:
        Follow nested .value attributes until reaching ast.Name.

        Example:
            database.user.save()

            Collected in reverse:
                ["save", "user", "database"]

            Reversed:
                ["database", "user", "save"]

            Result:
                ("save", "database.user")

    Notes
    -----
    This does not determine which repository definition is called.
    It only preserves the syntactic name and qualifier.
    """
    if isinstance(func, ast.Name):
        return func.id, None

    if isinstance(func, ast.Attribute):
        attributes = []
        current = func

        while isinstance(current, ast.Attribute):
            attributes.append(current.attr)
            current = current.value

        if not isinstance(current, ast.Name):
            return None

        attributes.append(current.id)
        attributes.reverse()

        return attributes[-1], ".".join(attributes[:-1])

    return None


def resolve_self_call(
    call: CodeCall,
    symbol_index: dict[str, list[CodeChunk]],
    chunk_by_id: dict[str, CodeChunk]
) -> CodeDependency | None:
    """
    Resolve a self.method() call to a method in the caller's class.

    Parameters
    ----------
    call : CodeCall
        Raw call to resolve.

        Expected:
            call.qualifier == "self"

        Example:
            CodeCall(
                caller_id="users.py::method::User.update::5",
                callee_name="save",
                qualifier="self"
            )

    symbol_index : dict[str, list[CodeChunk]]
        Maps symbol names to candidate definitions.

        Format:
            {
                "User.save": [CodeChunk(...)],
                "save": [CodeChunk(...)]
            }

    chunk_by_id : dict[str, CodeChunk]
        Maps unique chunk IDs to their CodeChunk objects.

        Format:
            {
                "users.py::method::User.update::5": CodeChunk(...)
            }

    Returns
    -------
    CodeDependency | None
        A resolved caller-to-callee relationship.

        Example:
            CodeDependency(
                caller_id="users.py::method::User.update::5",
                callee_id="users.py::method::User.save::10"
            )

        Returns None if:
            - The qualifier is not "self".
            - The caller chunk cannot be found.
            - The caller is not a METHOD.
            - No matching same-file method exists.
            - Multiple matching methods are found.

    Resolution
    ----------
    For:
        class User:
            def update(self):
                self.save()

            def save(self):
                pass

    1. Find caller chunk: User.update
    2. Extract class name: User
    3. Construct qualified name: User.save
    4. Search symbol_index["User.save"]
    5. Filter by the caller's file and METHOD type
    6. Resolve only if exactly one candidate remains

    Limitations
    -----------
    Does not currently support inherited methods or reassigned
    receivers. Assumes `self` represents the current class instance.
    """
    if call.qualifier != "self":
        return None

    caller = chunk_by_id.get(call.caller_id)

    if caller is None:
        return None

    if caller.type != ChunkType.METHOD:
        return None

    class_name = caller.name.rsplit(".", 1)[0]

    qualified_name = f"{class_name}.{call.callee_name}"

    candidates = symbol_index.get(qualified_name, [])

    candidates = [
        candidate
        for candidate in candidates
        if candidate.path == caller.path
        and candidate.type == ChunkType.METHOD
    ]

    if len(candidates) != 1:
        return None

    return CodeDependency(
        caller_id=call.caller_id,
        callee_id=candidates[0].id
    )


def resolve_unqualified_call(
    call: CodeCall,
    symbol_index: dict[str, list[CodeChunk]],
    chunk_by_id: dict[str, CodeChunk]
) -> CodeDependency | None:
    """
    Resolve an unqualified function call such as `save()`.

    Resolution strategy:

    1. Look up symbols matching the called name.
    2. Keep only top-level function chunks.
    3. Find the caller chunk.
    4. Prefer a unique function defined in the same file.
    5. If no same-file function exists, resolve only when there is
       exactly one matching function in the repository.
    6. Otherwise, leave the call unresolved.

    This intentionally does not model full Python lexical scoping or
    import behavior. Import-aware resolution will be handled separately.

    Args:
        call:
            The function call being resolved.

        symbol_index:
            Mapping from symbol names to possible CodeChunk definitions.

        chunk_by_id:
            Mapping from chunk IDs to their exact CodeChunk objects.

    Returns:
        A CodeDependency when the call can be resolved confidently,
        otherwise None.
    """

    candidates = symbol_index.get(call.callee_name, [])

    function_candidates = [
        candidate
        for candidate in candidates
        if candidate.type == ChunkType.FUNCTION
    ]

    if not function_candidates:
        return None

    caller = chunk_by_id.get(call.caller_id)

    if caller is None:
        return None

    same_file_candidates = [
        candidate
        for candidate in function_candidates
        if candidate.path == caller.path
    ]

    if len(same_file_candidates) == 1:
        return CodeDependency(
            caller_id=call.caller_id,
            callee_id=same_file_candidates[0].id,
        )

    if len(same_file_candidates) > 1:
        return None

    if len(function_candidates) == 1:
        return CodeDependency(
            caller_id=call.caller_id,
            callee_id=function_candidates[0].id,
        )

    return None


def resolve_call(
    call: CodeCall,
    symbol_index: dict[str, list[CodeChunk]],
    chunk_by_id: dict[str, CodeChunk],
    imports_by_file: dict[
        str, dict[str, tuple[str, str | None]]
    ] = None
) -> CodeDependency | None:
    """
    Resolve one raw CodeCall to a repository CodeDependency.

    Parameters
    ----------
    call : CodeCall
        Unresolved call containing:
            caller_id
            callee_name
            qualifier

    symbol_index : dict[str, list[CodeChunk]]
        Name-to-candidate-definitions lookup.

    chunk_by_id : dict[str, CodeChunk]
        Exact chunk-ID-to-CodeChunk lookup.

    Returns
    -------
    CodeDependency | None
        A dependency containing exact caller and callee chunk IDs.

        Example:
            CodeDependency(
                caller_id="main.py::function::run::1",
                callee_id="utils.py::function::multiply::3"
            )

        Returns None if the call cannot be resolved unambiguously.

    Current Rules
    -------------
    1. qualifier == "self":
        Attempt same-class method resolution using resolve_self_call().

    2. qualifier is not None:
        Leave unresolved (other object/module qualifiers unsupported).

    3. qualifier is None:
        Search the symbol index by callee_name.

        Zero candidates     -> None
        One candidate       -> CodeDependency
        Multiple candidates -> None

    Limitations
    -----------
    Unqualified calls still use global name matching and may
    incorrectly match class methods. We will improve this next.
    """
    if call.qualifier == "self":
        return resolve_self_call(
            call,
            symbol_index,
            chunk_by_id
        )

    if call.qualifier is None:
        caller = chunk_by_id.get(call.caller_id)

        if caller is None:
            return None

        file_imports = (
            imports_by_file.get(caller.path, {})
            if imports_by_file is not None
            else {}
        )

        imported = file_imports.get(call.callee_name)

        # Resolve explicitly imported functions first.
        if imported is not None and imported[1] is not None:
            return resolve_direct_import(
                call,
                symbol_index,
                chunk_by_id,
                imports_by_file
            )

        # An imported module name is not itself a function
        if imported is not None:
            return None

        return resolve_unqualified_call(
            call,
            symbol_index,
            chunk_by_id
        )

    if imports_by_file is not None:
        return resolve_module_call(
            call,
            symbol_index,
            chunk_by_id,
            imports_by_file
        )

    return None


def resolve_calls(
    calls: list[CodeCall],
    symbol_index: dict[str, list[CodeChunk]],
    chunk_by_id: dict[str, CodeChunk]
) -> list[CodeDependency]:
    """
    Resolve a collection of raw calls into repository dependencies.

    Parameters
    ----------
    calls : list[CodeCall]
        Calls previously extracted from function/method chunks.

    symbol_index : dict[str, list[CodeChunk]]
        Maps names to candidate repository definitions.

    chunk_by_id : dict[str, CodeChunk]
        Maps exact chunk IDs to their CodeChunk objects.

    Returns
    -------
    list[CodeDependency]
        Only the successfully resolved dependencies.

        Example:
            Input calls:
                multiply()
                print()
                self.save()

            Possible output:
                [
                    CodeDependency(caller_id, multiply_chunk_id),
                    CodeDependency(caller_id, save_method_chunk_id)
                ]

        An unresolved call such as print() is omitted if no
        matching repository symbol exists.

        Returns [] if no calls can be resolved.

    Processing
    ----------
    1. Iterate through all CodeCall objects.
    2. Pass each call to resolve_call().
    3. Append non-None dependencies to the result.
    4. Return the list of resolved dependencies.
    """
    dependencies = []

    for call in calls:
        dependency = resolve_call(
            call,
            symbol_index,
            chunk_by_id
        )

        if dependency is not None:
            dependencies.append(dependency)

    return dependencies


def extract_imports(
    source: str
) -> dict[str, tuple[str, str | None]]:
    """
    Extract basic import bindings from Python source code.

    Maps names available in the importing module to their
    original module and optionally imported symbol.

    For example:
        import utils as u
        from database import save as persist

    Returns:
        {
            "u": ("utils", None),
            "persist": ("database", "save")
        }

    Args:
        source: Complete Python source code of a file.

    Returns:
        A dictionary mapping locally bound import names to
        (module_path, imported_symbol) tuples.

    Limitations:
        Only absolute imports at module scope are supported.
        Star imports, relative imports, and imports inside
        functions/classes are not handled yet.
    """
    tree = ast.parse(source)
    imports = {}

    for node in tree.body:

        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = (
                    alias.asname
                    if alias.asname
                    else alias.name.split(".")[0]
                )

                imports[local_name] = (
                    alias.name if alias.asname else local_name,
                    None
                )

        elif isinstance(node, ast.ImportFrom):

            if node.module is None or node.level > 0:
                continue

            for alias in node.names:
                if alias.name == "*":
                    continue

                local_name = alias.asname or alias.name

                imports[local_name] = (
                    node.module,
                    alias.name
                )

    return imports


def resolve_module_call(
    call: CodeCall,
    symbol_index: dict[str, list[CodeChunk]],
    chunk_by_id: dict[str, CodeChunk],
    imports_by_file: dict[
        str, dict[str, tuple[str, str | None]]
    ],
) -> CodeDependency | None:
    """
    Resolve a module-qualified function call such as utils.save().

    The qualifier must correspond to an imported module in the
    caller's file.

    Args:
        call:
            Extracted function call containing the callee name
            and qualifier.

        symbol_index:
            Maps symbol names to possible definitions.

        chunk_by_id:
            Maps exact chunk IDs to CodeChunk objects.

        imports_by_file:
            Maps source file paths to their extracted imports.

    Returns:
        A CodeDependency if exactly one matching top-level
        function is found, otherwise None.

    Limitations:
        Supports simple absolute module imports.
        Does not resolve object methods, re-exports, or
        relative imports.
    """

    if call.qualifier is None:
        return None

    caller = chunk_by_id.get(call.caller_id)

    if caller is None:
        return None

    file_imports = imports_by_file.get(caller.path, {})

    imported = file_imports.get(call.qualifier)

    if imported is None:
        return None

    module_name, imported_symbol = imported

    # This helper handles imported modules, not imported functions.
    if imported_symbol is not None:
        return None

    # Convert dotted Python module names into repository paths.
    expected_path = module_name.replace(".", "/") + ".py"

    candidates = symbol_index.get(call.callee_name, [])

    matching_functions = [
        candidate
        for candidate in candidates
        if (
            candidate.type == ChunkType.FUNCTION
            and candidate.path == expected_path
        )
    ]

    if len(matching_functions) != 1:
        return None

    return CodeDependency(
        caller_id=call.caller_id,
        callee_id=matching_functions[0].id,
    )


def resolve_direct_import(
    call: CodeCall,
    symbol_index: dict[str, list[CodeChunk]],
    chunk_by_id: dict[str, CodeChunk],
    imports_by_file: dict[
        str, dict[str, tuple[str, str | None]]
    ],
) -> CodeDependency | None:
    """
    Resolve functions imported using:
        from utils import save
        from utils import save as persist

    Args:
        call:
            An unqualified CodeCall.

        symbol_index:
            Maps symbol names to candidate definitions.

        chunk_by_id:
            Maps chunk IDs to exact chunks.

        imports_by_file:
            Import bindings for each repository file.

    Returns:
        A CodeDependency if exactly one matching function
        is found, otherwise None.
    """
    if call.qualifier is not None:
        return None

    caller = chunk_by_id.get(call.caller_id)

    if caller is None:
        return None

    file_imports = imports_by_file.get(caller.path, {})
    imported = file_imports.get(call.callee_name)

    if imported is None:
        return None

    module_name, imported_symbol = imported

    # Only handle direct function imports.
    if imported_symbol is None:
        return None

    expected_path = module_name.replace(".", "/") + ".py"

    candidates = symbol_index.get(imported_symbol, [])

    matches = [
        candidate
        for candidate in candidates
        if (
            candidate.type == ChunkType.FUNCTION
            and candidate.path == expected_path
        )
    ]

    if len(matches) != 1:
        return None

    return CodeDependency(
        caller_id=call.caller_id,
        callee_id=matches[0].id,
    )

# testing - remove app from app.models from the import statement to run
source = """
import utils
import database as db
from helpers import validate
from services.user import save as persist
"""

if __name__ == "__main__":
    print(extract_imports(source))
