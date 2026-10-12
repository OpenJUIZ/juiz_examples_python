from juiz import juiz_process


@juiz_process
def increment_process_python(arg1: int = 0):
    """引数に 1 を足して返す"""
    print(f"increment_process_python: {arg1} -> {arg1 + 1}")
    return arg1 + 1
