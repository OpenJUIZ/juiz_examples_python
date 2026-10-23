from juiz import juiz_process


@juiz_process
def talker_python(message: str = "Hello, World!") -> str:
    """文字列 message (既定は "Hello, World!") を出力する"""
    print(f'talker_python says "{message}"')
    return message
