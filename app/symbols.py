from collections import defaultdict

from app.models import CodeChunk, ChunkType

"""
    Function to build a dictionary mapping symbols to their respective CodeChunk(s)
    Each entry in the dictionary has a list value as there might be multiple CodeChunk(s) with the same name
    This just answers what definitions in the respoitory match this name
    @fields:
        -chunks: list of CodeChunk
"""
def build_symbol_index(
    chunks: list[CodeChunk]
) -> dict[str, list[CodeChunk]]:

    symbol_index = defaultdict(list)

    for chunk in chunks:

        if chunk.type in {
            ChunkType.FUNCTION,
            ChunkType.CLASS,
        }:
            symbol_index[chunk.name].append(chunk)

        elif chunk.type == ChunkType.METHOD:
            symbol_index[chunk.name].append(chunk)

            # extracting just the method name without class
            short_name = chunk.name.split(".")[-1]

            # duplicating a code chunk for method name
            symbol_index[short_name].append(chunk)

    return dict(symbol_index)