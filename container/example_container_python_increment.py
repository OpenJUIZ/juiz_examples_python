from juiz import juiz_container_process


@juiz_container_process(container_type="example_container_python")
def example_container_python_increment(container, arg1: int = 1):
    """Container の値に arg1 を足して、足した後の値を返す"""
    container.value = container.value + arg1
    return container.value
