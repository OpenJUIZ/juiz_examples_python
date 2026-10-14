# juiz_examples_python

ロボット・IoT 向けミドルウェア [juiz](https://github.com/OpenJUIZ/juiz) の Python 版サンプル集です。
juiz 本体は crates.io の [juiz_app](https://crates.io/crates/juiz_app) 0.0.12、Python 用パッケージは PyPI の [pyjuiz](https://pypi.org/project/pyjuiz/) 0.0.12 を使うので、juiz のソースを手元に置かずに試せます。

Rust 版のサンプルは [juiz_examples_rust](https://github.com/OpenJUIZ/juiz_examples_rust) にあります。

## しくみ

Python で書いた Process や Container は単体では動きません。`juiz` コマンド (Rust 製) が設定ファイル (`*.conf`) を読み、そこに書かれた Python ファイルを組み込みの Python インタプリタで読み込んで実行します。
そのため、`juiz` コマンドと `pyjuiz` パッケージの両方をインストールします。

## 必要なもの

- Linux または macOS
- Rust (stable)。インストールは https://rustup.rs/ を参照してください。
- Python 3 と、その開発用ライブラリ (Ubuntu なら `sudo apt install python3-dev python3-venv`)

## 1. juiz コマンドをインストールする

```sh
cargo install juiz_app
```

`juiz` コマンドが `~/.cargo/bin` に入ります。juiz はビルド時に見つけた Python (`python3`) を組み込むので、手順 2 でも同じ Python を使ってください。

## 2. pyjuiz をインストールする

```sh
git clone https://github.com/OpenJUIZ/juiz_examples_python.git
cd juiz_examples_python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

以降の手順は、この venv を有効にしたターミナルで実行してください。
設定ファイルは `./process` などの相対パスで Python ファイルを探すので、**リポジトリのルートで** `juiz` を実行してください。

## 3. 動かしてみる

### Process: increment_process

引数に 1 を足して返すだけの Process です ([process/increment_process_python.py](process/increment_process_python.py))。

```python
from juiz import juiz_process

@juiz_process
def increment_process_python(arg1: int = 0) -> int:
    return arg1 + 1
```

関数名とファイル名を同じにしておくと、juiz が設定ファイルの名前からファイルと関数を見つけます。引数の型と既定値は型ヒントと既定値から、出力の型は戻り値の型ヒント (`-> int` など) から自動で読み取られます。戻り値の型ヒントは省略できません。

```sh
juiz -f increment_process.conf -d
```

`-d` を付けると HTTP ブローカー (8000 番ポート) を立ち上げて待機します (Ctrl+C で終了)。
別のターミナルから呼び出せます。

```sh
juiz process list
juiz process call "http://127.0.0.1:8000/process/increment0::increment_process_python" '{"arg1": 3}' -p
# => CapsulePtr((value:Value(4), option: []))
```

ブラウザで http://127.0.0.1:8000/docs を開くと Swagger UI からも試せます。

`decrement_process.conf` も同じ使い方です (1 を引く Process)。

### Process の接続: talker / listener

`talker_python` の出力を `listener_python` の引数に Push 接続し、実行コンテキスト (main_loop_ec) で 1Hz で `talker_python` を動かします。

```sh
juiz -f talker_listener.conf -d
# talker_python says "Hello, World!"
# listener_python receives "Hello, World!"
# ...
```

### Container: example_container

状態 (整数値) を持つ Container と、それを操作する ContainerProcess (`example_container_python_increment`、`example_container_python_get`) のサンプルです ([container/](container/))。

```sh
juiz -f example_container.conf -d
```

別のターミナルから呼び出すたびに値が増えていきます。

```sh
juiz container-process call "http://127.0.0.1:8000/container_process/increment0::example_container_python_increment:container0" '{"arg1": 5}' -p
# => CapsulePtr((value:Value(5), option: []))
juiz container-process call "http://127.0.0.1:8000/container_process/get0::example_container_python_get:container0" '{}' -p
# => CapsulePtr((value:Value(5), option: []))
```

### Component: example_component

1 つの Python ファイルに Process・Container・ContainerProcess をまとめて入れる Component のサンプルです ([component/example_component_python.py](component/example_component_python.py))。
デコレータを付けた関数を juiz が自動で見つけるので、マニフェストを書く必要はありません。

```sh
juiz -f example_component.conf -d
juiz process call "http://127.0.0.1:8000/process/increment0::example_component_python_increment" '{"arg1": 1}' -p
# => CapsulePtr((value:Value(2), option: []))
juiz container-process call "http://127.0.0.1:8000/container_process/set0::example_component_python_container_set:container0" '{"value": 7}' -p
juiz container-process call "http://127.0.0.1:8000/container_process/get0::example_component_python_container_get:container0" '{}' -p
# => CapsulePtr((value:Value(7), option: []))
```

## 構成

| パス | 内容 |
| --- | --- |
| `process/` | Process (入力と出力を持つ冪等な関数) のサンプル |
| `container/` | Container (状態を持つ) と ContainerProcess のサンプル |
| `component/` | 複数の要素を 1 つのファイルにまとめた Component のサンプル |
| `*.conf` | 各サンプルを動かすための juiz の設定ファイル |
| `requirements.txt` | pyjuiz のバージョン指定 |

## うまく動かないとき

- `ModuleNotFoundError: No module named 'juiz'` や `setup_plugins ... failed` が出る場合は、pyjuiz を入れた venv が有効になっているか確認してください。それでも見つからない場合は `PYTHONPATH` に venv の site-packages を指定してください (例: `export PYTHONPATH=$(python -c 'import site; print(site.getsitepackages()[0])')`)。
- `PyJuizProcessReturnsUnknownTypeError` が出る場合は、Process の関数に戻り値の型ヒント (`-> int` など) が書かれているか確認してください。
- `AttributeError: module '' has no attribute ...` が出る場合は、ファイル名と関数名 (および設定ファイルの名前) がそろっているか確認してください。
