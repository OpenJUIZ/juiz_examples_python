from juiz import juiz_container


class PyContainer:
    def __init__(self, value: int):
        self.value = value


@juiz_container
def example_container_python(initial_value: int = 0):
    """整数値を 1 つ保持する Container"""
    return PyContainer(initial_value)
