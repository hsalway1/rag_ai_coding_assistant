
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


def resolve_call(
    call: CodeCall,
    symbol_index: dict[str, list[CodeChunk]],
    chunk_by_id: dict[str, CodeChunk]
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

    if call.qualifier is not None:
        return None

    candidates = symbol_index.get(call.callee_name, [])

    if len(candidates) != 1:
        return None

    callee = candidates[0]

    return CodeDependency(
        caller_id=call.caller_id,
        callee_id=callee.id
    )


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
