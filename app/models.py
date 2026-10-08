from dataclasses import dataclass
from enum import Enum

class ChunkType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"

"""
    This class is a representation of a file in working repository
    @fields:
        - path: path of the file relative to the working repository
        - language: programming language of the file
        - content: the whole code content of the file
"""
@dataclass
class RepositoryFile:
    path: str
    language: str
    content: str

"""
    This class is a represenatation of code chunks which will be passed to an embedding model
    @fields:
        - path: path of the file it is present in (could be class or method)
        - language: programming language of the file
        - type: class or method
        - name: name of the class or the method
        - start_line: starting line of the code chunk in the file
        - end_line: ending line of the code chunk in the file
        - content: code of the chunk
"""
@dataclass
class CodeChunk:
    id:str
    path:str
    language:str
    type:ChunkType
    name:str
    start_line:int
    end_line:int
    content:str

"""
    Class to represent a code call
    AST found that this chunk calls something with this name.
"""
@dataclass
class CodeCall:
    caller_id: str
    callee_name: str
    qualifier: str | None = None

"""
    Class to represent dependencies between code chunks
    Successfully resolved that call to another chunk in our repository.
    @fields:
        - caller: code chunk calling the callee
"""
@dataclass
class CodeDependency:
    caller_id: str
    callee_id: str

"""
    Function to create a unique id for chunks based on their file, name and start line

    This is useful to differentiate between two chunks having the same name
"""
def create_chunk_id(
    file: RepositoryFile,
    chunk_type: ChunkType,
    name: str,
    start_line: int
) -> str:
    return (
        f"{file.path}::{chunk_type.value}::{name}::{start_line}"
    )