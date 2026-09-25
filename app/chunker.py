import ast
from app.models import RepositoryFile, CodeChunk


def get_source(lines, node):
    start = node.lineno - 1
    end = node.end_lineno

    return "\n".join(lines[start:end])

def create_chunk(
        file: RepositoryFile,
        node,
        chunk_type: str,
        name: str,
        lines
):
    return CodeChunk(
        path=file.path,
        language=file.language,
        type=chunk_type,
        name=name,
        start_line=node.lineno,
        end_line=node.end_lineno,
        content=get_source(lines, node)
    )

def chunk_python_file(file: RepositoryFile) -> list[CodeChunk]:
    content = file.content

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    lines = content.splitlines()

    chunks = []

    for node in tree.body:

        if isinstance(node, ast.FunctionDef):

            chunks.append(
                create_chunk(
                    file,
                    node,
                    "function",
                    node.name,
                    lines
                )
            )

        elif isinstance(node, ast.ClassDef):

            chunks.append(
                create_chunk(
                    file,
                    node,
                    "class",
                    node.name,
                    lines
                )
            )

            for child in node.body:

                if isinstance(child, ast.FunctionDef):

                    chunks.append(
                        create_chunk(
                            file,
                            child,
                            "method",
                            f"{node.name}.{child.name}",
                            lines
                        )
                    )

    return chunks