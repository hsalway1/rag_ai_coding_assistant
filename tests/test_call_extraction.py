import ast
import unittest

from app.dependencies import get_call_name, get_function_calls
from app.models import CodeCall


class TestCallNameExtraction(unittest.TestCase):

    def extract(self, source):
        tree = ast.parse(source)
        call_node = tree.body[0].value

        return get_call_name(call_node.func)

    def test_simple_function_call(self):
        self.assertEqual(
            self.extract("save()"),
            ("save", None)
        )

    def test_self_method_call(self):
        self.assertEqual(
            self.extract("self.save()"),
            ("save", "self")
        )

    def test_object_method_call(self):
        self.assertEqual(
            self.extract("user.save()"),
            ("save", "user")
        )

    def test_module_function_call(self):
        self.assertEqual(
            self.extract("math_utils.add()"),
            ("add", "math_utils")
        )

    def test_nested_attribute_call(self):
        self.assertEqual(
            self.extract("database.user.save()"),
            ("save", "database.user")
        )

    def test_unsupported_dynamic_receiver(self):
        self.assertIsNone(
            self.extract("get_user().save()")
        )


class TestFunctionCallExtraction(unittest.TestCase):

    def extract(self, source):
        tree = ast.parse(source)
        function_node = tree.body[0]

        caller_id = "test.py::function::process::1"

        return get_function_calls(function_node, caller_id)

    def test_single_function_call(self):
        source = """
def process():
    save()
"""
        calls = self.extract(source)

        self.assertEqual(len(calls), 1)
        self.assertIsInstance(calls[0], CodeCall)
        self.assertEqual(calls[0].callee_name, "save")
        self.assertIsNone(calls[0].qualifier)
        self.assertEqual(
            calls[0].caller_id,
            "test.py::function::process::1"
        )

    def test_multiple_calls(self):
        source = """
def process():
    save()
    self.update()
    database.user.delete()
"""
        calls = self.extract(source)

        self.assertEqual(len(calls), 3)

        extracted = {
            (call.callee_name, call.qualifier)
            for call in calls
        }

        expected = {
            ("save", None),
            ("update", "self"),
            ("delete", "database.user")
        }

        self.assertEqual(extracted, expected)

    def test_no_function_calls(self):
        source = """
def process():
    x = 10
    y = x + 20
    return y
"""
        calls = self.extract(source)

        self.assertEqual(calls, [])

    def test_nested_control_flow(self):
        source = """
def process():
    if True:
        save()

    for i in range(3):
        print(i)
"""
        calls = self.extract(source)

        extracted_names = {
            call.callee_name
            for call in calls
        }

        self.assertEqual(
            extracted_names,
            {"save", "range", "print"}
        )

    def test_unsupported_call(self):
        source = """
def process():
    get_user().save()
"""
        calls = self.extract(source)

        # The outer .save() is unsupported, but the
        # inner get_user() is still a valid ast.Call.
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].callee_name, "get_user")
        self.assertIsNone(calls[0].qualifier)


if __name__ == "__main__":
    unittest.main()