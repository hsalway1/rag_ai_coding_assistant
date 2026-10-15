import unittest

from app.graph import build_dependency_graph, get_dependencies
from app.models import CodeDependency


class TestDependencyGraph(unittest.TestCase):

    def test_build_dependency_graph(self):
        dependencies = [
            CodeDependency(caller_id="A", callee_id="B"),
            CodeDependency(caller_id="A", callee_id="C"),
            CodeDependency(caller_id="A", callee_id="B"),
            CodeDependency(caller_id="B", callee_id="D"),
        ]

        graph = build_dependency_graph(dependencies)

        expected = {
            "A": {"B", "C"},
            "B": {"D"},
        }

        self.assertEqual(graph, expected)

    def test_empty_dependencies(self):
        graph = build_dependency_graph([])

        self.assertEqual(graph, {})

    def test_direct_dependencies(self):
        graph = {
            "A": {"B", "C"},
            "B": {"D"},
            "C": set()
        }

        result = get_dependencies(graph, "A", max_depth=1)

        self.assertEqual(result, ["B", "C"])


    def test_two_level_dependencies(self):
        graph = {
            "A": {"B", "C"},
            "B": {"D"},
            "C": {"E"}
        }

        result = get_dependencies(graph, "A", max_depth=2)

        self.assertEqual(result, ["B", "C", "D", "E"])


    def test_cycle_handling(self):
        graph = {
            "A": {"B"},
            "B": {"C"},
            "C": {"A"}
        }

        result = get_dependencies(graph, "A", max_depth=5)

        self.assertEqual(result, ["B", "C"])


    def test_zero_depth(self):
        graph = {"A": {"B"}}

        result = get_dependencies(graph, "A", max_depth=0)

        self.assertEqual(result, [])

    def test_negative_depth(self):
        with self.assertRaises(ValueError):
            get_dependencies({"A": {"B"}}, "A", max_depth=-1)

if __name__ == "__main__":
    unittest.main()