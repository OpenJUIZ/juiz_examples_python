from juiz import juiz_process


@juiz_process
def listener_python(arg1: str = "Hello, Juiz!"):
    """受け取った文字列を表示する"""
    print(f'listener_python receives "{arg1}"')
    return arg1
