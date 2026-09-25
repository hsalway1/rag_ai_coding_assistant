from dataclasses import dataclass

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
    path:str
    language:str
    type:str
    name:str
    start_line:int
    end_line:int
    content:str