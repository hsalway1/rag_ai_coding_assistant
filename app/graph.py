from collections import defaultdict

from app.models import CodeDependency


def build_dependency_graph(
    dependencies: list[CodeDependency]
) -> dict[str, set[str]]:
    """
    Build a directed dependency graph from resolved code dependencies.

    Each node represents a code chunk, identified by its unique
    chunk ID. An edge from A to B means that chunk A calls chunk B.

    Args:
        dependencies:
            A list of resolved CodeDependency objects, each containing
            a caller_id and a callee_id.

    Returns:
        A dictionary representing the graph as an adjacency list.

        Each key is a caller chunk ID, and its value is a set
        containing the IDs of chunks it calls.

        Duplicate dependencies are automatically removed.

        Example:
            Input:
                A -> B
                A -> C
                A -> B
                B -> D

            Output:
                {
                    "A": {"B", "C"},
                    "B": {"D"}
                }

        Returns an empty dictionary if no dependencies are provided.

        Nodes without outgoing dependencies are not explicitly included.
    """

    graph = defaultdict(set)

    for dependency in dependencies:
        graph[dependency.caller_id].add(dependency.callee_id)

    return dict(graph)


from collections import deque


def get_dependencies(
    graph: dict[str, set[str]],
    start_id: str,
    max_depth: int = 1
) -> list[str]:
    """
    Find dependencies reachable from a starting code chunk.

    Uses breadth-first search (BFS) to explore dependencies
    up to a specified maximum depth.

    Args:
        graph:
            Adjacency list mapping caller chunk IDs to sets
            of callee chunk IDs.

        start_id:
            ID of the code chunk whose dependencies we want.

        max_depth:
            Maximum number of dependency edges to traverse.
            A depth of 1 returns direct dependencies only.
            A depth of 2 includes dependencies of dependencies.

    Returns:
        List of reachable chunk IDs, excluding start_id.

        Each dependency appears at most once. Cycles are
        handled using a visited set.

        Returns an empty list if no dependencies are found.

    Raises:
        ValueError:
            If max_depth is negative.
    """
    if max_depth < 0:
        raise ValueError("max_depth cannot be negative")

    visited = {start_id}
    queue = deque([(start_id, 0)])
    result = []

    while queue:
        current_id, depth = queue.popleft()

        if depth >= max_depth:
            continue

        for neighbor_id in sorted(graph.get(current_id, set())):
            if neighbor_id in visited:
                continue

            visited.add(neighbor_id)
            result.append(neighbor_id)
            queue.append((neighbor_id, depth + 1))

    return result