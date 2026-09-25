from app.repository import load_repository
from app.chunker import chunk_python_file

files = load_repository("sample_repo")

all_chunks = []

# file is of type models.RepositoryFile
for file in files:
    if file.language == "python":
        chunks = chunk_python_file(file)
        all_chunks.extend(chunks)

# chunk is of type models.CodeChunk
for chunk in all_chunks:
    print("=" * 50)
    print(chunk.path)
    print(chunk.type)
    print(chunk.name)
    print(chunk.start_line)
    print(chunk.end_line)
    print(chunk.content)