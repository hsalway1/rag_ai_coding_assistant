from sentence_transformers import SentenceTransformer

from app.models import CodeChunk

"""
    This class is a semantic retriever that embeds code chunks and finds the most relevant ones for a query.
    @fields:
        - chunks: list of code chunks to index and search over
        - model: sentence-transformers model used to encode text into embeddings
        - embeddings: embedding vectors generated for each code chunk
"""
class SemanticRetriever:
    """
        Initialize the retriever by encoding all code chunks into embeddings.
        @params:
            - chunks: list of code chunks to index
    """
    def __init__(self, chunks: list[CodeChunk]):
        self.chunks = chunks

        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        documents = [
            self.chunk_to_text(chunk)
            for chunk in chunks
        ]

        self.embeddings = self.model.encode(documents)

    """
        Convert a code chunk into a plain-text document that can be embedded semantically.
        @params:
            - chunk: code chunk to be transformed into text
        @returns:
            - text representation of the chunk with its file, type, and name information
    """
    def chunk_to_text(self, chunk: CodeChunk) -> str:
        # not including start_lineno and end_lineno since they have no semantic meanings
        return (
            f"File: {chunk.path}\n"
            f"Type: {chunk.type}\n"
            f"Name: {chunk.name}\n\n"
            f"{chunk.content}"
        )

    """
        Search for the most relevant code chunks for a given query.
        @params:
            - query: search text to evaluate against the indexed chunks
            - top_k: number of most similar code chunks to return
        @returns:
            - list of tuples containing the matching chunk and its similarity score
    """
    def search(self, query: str, top_k: int = 3, min_score: float = 0.4) -> list[tuple[CodeChunk, float]]:
        query_embedding = self.model.encode(query)

        similarities = self.model.similarity(
            query_embedding,
            self.embeddings
        )[0]

        # this does not return the scores, this returns their indices in sorted order
        ranked_indices = similarities.argsort(
            descending=True
        )

        results = []

        # get the top k results
        for index in ranked_indices:
            chunk = self.chunks[index]
            score = similarities[index].item()

            if score < min_score:
                continue

            results.append((chunk, score))

        return results