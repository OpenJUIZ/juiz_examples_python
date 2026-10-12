from juiz import juiz_container_process


@juiz_container_process(container_type="example_container_python")
def example_container_python_get(container):
    """Container の値を返す"""
    return container.value
