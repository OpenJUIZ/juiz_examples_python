from juiz import juiz_container, juiz_container_process, juiz_process


@juiz_process
def example_component_python_increment(arg1: int = 0) -> int:
    """引数に 1 を足して返す"""
    return arg1 + 1


class IntegerContainer:
    def __init__(self, value: int):
        self.value = value


@juiz_container
def example_component_python_container(initial_value: int = 0) -> IntegerContainer:
    """整数値を 1 つ保持する Container"""
    return IntegerContainer(initial_value)


@juiz_container_process(container_type="example_component_python_container")
def example_component_python_container_set(container, value: int = 0) -> int:
    """Container の値を設定する"""
    container.value = value
    return container.value


@juiz_container_process(container_type="example_component_python_container")
def example_component_python_container_get(container) -> int:
    """Container の値を返す"""
    return container.value
