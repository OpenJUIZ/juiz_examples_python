from juiz import juiz_process


@juiz_process
def decrement_process_python(arg1: int = 0):
    """引数から 1 を引いて返す"""
    print(f"decrement_process_python: {arg1} -> {arg1 - 1}")
    return arg1 - 1
