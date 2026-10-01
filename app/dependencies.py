import ast
import textwrap

from app.models import CodeChunk, CodeCall, ChunkType

def get_function_calls(node):
    calls = []

    # ast.walk recursively walks through everything inside the node
    for child in ast.walk(node):
        # if child is not a function call
        if not isinstance(child, ast.Call):
            continue
            
        # child.func is the thing being called
        # ex: Name(id='multiply')
        if isinstance(child.func, ast.Name):
            calls.append(child.func.id)

        elif isinstance(child.func, ast.Attribute):
            calls.append(child.func.attr)

    return calls

def extract_chunk_calls(
    chunk: CodeChunk
) -> list[CodeCall]:

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

        callees = get_function_calls(node)

        for callee_name in callees:
            calls.append(
                CodeCall(
                    caller_id=chunk.id,
                    callee_name=callee_name
                )
            )

    return calls

code = """
def calculate(a, b):
    result = multiply(a, b)
    print(result)
    return result

def dance(a, b):
    result = dash(a, b)
    print(result)
    return result
"""

# testing the function
if __name__ == "__main__":
    tree = ast.parse(code)

    function_node = tree.body[0]

    print(get_function_calls(function_node))