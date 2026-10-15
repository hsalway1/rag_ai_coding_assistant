from app.models import CodeChunk
from app.graph import get_dependencies
from app.retriever import SemanticRetriever


def expand_context(
    retrieved_chunks: list[CodeChunk],
    graph: dict[str, set[str]],
    chunk_by_id: dict[str, CodeChunk],
    max_depth: int = 1,
    max_chunks: int = 10
) -> list[CodeChunk]:
    """
    Expand retrieved code chunks with their dependencies.

    Args:
        retrieved_chunks:
            Initial code chunks selected by semantic retrieval,
            ordered by relevance.

        graph:
            Dependency graph mapping caller IDs to callee IDs.

        chunk_by_id:
            Lookup mapping chunk IDs to CodeChunk objects.

        max_depth:
            Maximum dependency traversal depth.

        max_chunks:
            Maximum number of code chunks in the final context.

    Returns:
        An ordered list containing retrieved chunks followed by
        their dependencies, without duplicate chunks.

        Retrieved chunks are prioritized over dependencies.
        Missing dependency IDs are ignored.
    """
    if max_chunks < 0:
        raise ValueError("max_chunks cannot be negative")

    if max_depth < 0:
        raise ValueError("max_depth cannot be negative")

    context = []
    seen = set()

    # Preserve the initial semantic retrieval results.
    for chunk in retrieved_chunks:
        if len(context) >= max_chunks:
            return context

        if chunk.id not in seen:
            context.append(chunk)
            seen.add(chunk.id)

    # Expand dependencies after preserving the retrieved results.
    for chunk in retrieved_chunks:
        dependency_ids = get_dependencies(
            graph,
            chunk.id,
            max_depth=max_depth
        )

        for dependency_id in dependency_ids:
            if len(context) >= max_chunks:
                return context

            if dependency_id in seen:
                continue

            dependency_chunk = chunk_by_id.get(dependency_id)

            if dependency_chunk is None:
                continue

            context.append(dependency_chunk)
            seen.add(dependency_id)

    return context


from app.retriever import SemanticRetriever


def retrieve_context(
    question: str,
    retriever: SemanticRetriever,
    graph: dict[str, set[str]],
    chunk_by_id: dict[str, CodeChunk],
    top_k: int = 3,
    max_depth: int = 1,
    max_chunks: int = 10
) -> list[CodeChunk]:
    """
    Retrieve semantically relevant code and expand its dependencies.

    Args:
        question:
            Natural-language question about the repository.

        retriever:
            Initialized SemanticRetriever containing indexed code chunks.

        graph:
            Directed dependency graph mapping caller IDs to callee IDs.

        chunk_by_id:
            Mapping from chunk IDs to their corresponding CodeChunk objects.

        top_k:
            Number of semantic search results to retrieve.

        max_depth:
            Maximum dependency traversal depth.

        max_chunks:
            Maximum number of chunks in the final context.

    Returns:
        Ordered list of CodeChunk objects containing semantically
        retrieved chunks followed by their dependencies.

        Duplicate chunks are removed by expand_context().
    """

    results = retriever.search(
        question,
        top_k=top_k
    )

    retrieved_chunks = [
        chunk
        for chunk, score in results
    ]

    return expand_context(
        retrieved_chunks=retrieved_chunks,
        graph=graph,
        chunk_by_id=chunk_by_id,
        max_depth=max_depth,
        max_chunks=max_chunks
    )