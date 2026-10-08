from app.repository import load_repository
from app.chunker import chunk_python_file
# from app.retriever import SemanticRetriever
from app.dependencies import extract_chunk_calls, resolve_calls

from app.symbols import build_symbol_index

files = load_repository("sample_repo")

all_chunks = []
all_calls = []

# file is of type models.RepositoryFile
for file in files:
    if file.language == "python":
        chunks = chunk_python_file(file)
        all_chunks.extend(chunks)

for chunk in all_chunks:
    all_calls.extend(
        extract_chunk_calls(chunk)
    )

chunk_by_id = {
    chunk.id: chunk for chunk in all_chunks
}

symbol_index = build_symbol_index(all_chunks)

dependencies = resolve_calls(
    all_calls,
    symbol_index
)

for dependency in dependencies:
    print(
        dependency.caller_id,
        "->",
        dependency.callee_id
    )

# for call in all_calls:
#     print(
#         call.caller_id,
#         "->",
#         call.callee_name
#     )

# retriever = SemanticRetriever(all_chunks)

# results = retriever.search(
#     "Where is multiplication performed?"
# )

# # chunk is of type models.CodeChunk
# for chunk, score in results:
#     print("=" * 50)
#     print("SCORE:", score)
#     print("FILE:", chunk.path)
#     print("TYPE:", chunk.type)
#     print("NAME:", chunk.name)
#     print("LINES:", chunk.start_line, "-", chunk.end_line)
#     print(chunk.content)