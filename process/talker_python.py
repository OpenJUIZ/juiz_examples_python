from juiz import juiz_process


@juiz_process
def talker_python():
    """文字列を出力する"""
    print('talker_python says "Hello, World!"')
    return "Hello, World!"
