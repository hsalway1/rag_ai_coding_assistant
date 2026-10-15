import unittest

from app.context import expand_context
from app.models import CodeChunk, ChunkType
from unittest.mock import Mock
from app.context import retrieve_context


class TestContextExpansion(unittest.TestCase):

    def setUp(self):
        """
        Create reusable code chunks and a dependency graph
        for testing context expansion.

        Dependency graph:

            A -> B -> D
            |    |
            v    v
            C    C

        A calls B and C.
        B calls C and D.
        """

        self.chunk_a = CodeChunk(
            id="main.py::function::A::1",
            path="main.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="A",
            start_line=1,
            end_line=2,
            content="def A():\n    B()\n    C()"
        )

        self.chunk_b = CodeChunk(
            id="utils.py::function::B::1",
            path="utils.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="B",
            start_line=1,
            end_line=2,
            content="def B():\n    C()\n    D()"
        )

        self.chunk_c = CodeChunk(
            id="utils.py::function::C::5",
            path="utils.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="C",
            start_line=5,
            end_line=6,
            content="def C():\n    pass"
        )

        self.chunk_d = CodeChunk(
            id="utils.py::function::D::9",
            path="utils.py",
            language="python",
            type=ChunkType.FUNCTION,
            name="D",
            start_line=9,
            end_line=10,
            content="def D():\n    pass"
        )

        self.chunk_by_id = {
            chunk.id: chunk
            for chunk in [
                self.chunk_a,
                self.chunk_b,
                self.chunk_c,
                self.chunk_d
            ]
        }

        self.graph = {
            self.chunk_a.id: {
                self.chunk_b.id,
                self.chunk_c.id
            },
            self.chunk_b.id: {
                self.chunk_c.id,
                self.chunk_d.id
            }
        }

    def test_direct_dependency_expansion(self):
        """Depth 1 should include only direct dependencies."""

        result = expand_context(
            retrieved_chunks=[self.chunk_a],
            graph=self.graph,
            chunk_by_id=self.chunk_by_id,
            max_depth=1
        )

        result_ids = [chunk.id for chunk in result]

        self.assertEqual(result_ids[0], self.chunk_a.id)

        self.assertEqual(
            set(result_ids),
            {
                self.chunk_a.id,
                self.chunk_b.id,
                self.chunk_c.id
            }
        )

        self.assertNotIn(self.chunk_d.id, result_ids)

    def test_deduplication(self):
        """
        A chunk should appear only once even when it is
        retrieved directly and discovered through dependencies.
        """

        result = expand_context(
            retrieved_chunks=[
                self.chunk_a,
                self.chunk_c
            ],
            graph=self.graph,
            chunk_by_id=self.chunk_by_id,
            max_depth=2
        )

        result_ids = [chunk.id for chunk in result]

        self.assertEqual(
            len(result_ids),
            len(set(result_ids))
        )

        self.assertEqual(
            result_ids[:2],
            [self.chunk_a.id, self.chunk_c.id]
        )

    def test_missing_dependency(self):
        """Dependencies with unknown chunk IDs should be ignored."""

        graph = {
            self.chunk_a.id: {"nonexistent_chunk"}
        }

        result = expand_context(
            retrieved_chunks=[self.chunk_a],
            graph=graph,
            chunk_by_id=self.chunk_by_id,
            max_depth=1
        )

        self.assertEqual(result, [self.chunk_a])

    def test_maximum_depth(self):
        """
        Depth 1 excludes D, while depth 2 includes D
        through the path A -> B -> D.
        """

        depth_one = expand_context(
            retrieved_chunks=[self.chunk_a],
            graph=self.graph,
            chunk_by_id=self.chunk_by_id,
            max_depth=1
        )

        depth_two = expand_context(
            retrieved_chunks=[self.chunk_a],
            graph=self.graph,
            chunk_by_id=self.chunk_by_id,
            max_depth=2
        )

        depth_one_ids = {chunk.id for chunk in depth_one}
        depth_two_ids = {chunk.id for chunk in depth_two}

        self.assertNotIn(self.chunk_d.id, depth_one_ids)
        self.assertIn(self.chunk_d.id, depth_two_ids)

    def test_maximum_chunks(self):
        """
        The total context should respect max_chunks,
        prioritizing retrieved chunks over dependencies.
        """

        result = expand_context(
            retrieved_chunks=[
                self.chunk_a,
                self.chunk_c
            ],
            graph=self.graph,
            chunk_by_id=self.chunk_by_id,
            max_depth=2,
            max_chunks=2
        )

        self.assertEqual(
            [chunk.id for chunk in result],
            [self.chunk_a.id, self.chunk_c.id]
        )

    def test_empty_retrieval(self):
        """No retrieved chunks should produce an empty context."""

        result = expand_context(
            retrieved_chunks=[],
            graph=self.graph,
            chunk_by_id=self.chunk_by_id
        )

        self.assertEqual(result, [])

    def test_retrieve_context(self):
        """Verify semantic retrieval feeds into dependency expansion."""

        mock_retriever = Mock()

        mock_retriever.search.return_value = [
            (self.chunk_a, 0.95)
        ]

        result = retrieve_context(
            question="How does A work?",
            retriever=mock_retriever,
            graph=self.graph,
            chunk_by_id=self.chunk_by_id,
            top_k=1,
            max_depth=1
        )

        result_ids = {chunk.id for chunk in result}

        self.assertEqual(
            result_ids,
            {
                self.chunk_a.id,
                self.chunk_b.id,
                self.chunk_c.id
            }
        )

        mock_retriever.search.assert_called_once_with(
            "How does A work?",
            top_k=1
        )


if __name__ == "__main__":
    unittest.main()