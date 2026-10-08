class Calculator:

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        self.add(a, b) # just for testing
        return a - b

    def calculate():
        result = multiply(5, 10)
        print(result)
        return result


def multiply(a, b):
    return a * b