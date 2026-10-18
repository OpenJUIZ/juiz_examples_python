# juiz_examples_python

ロボット・IoT 向けミドルウェア [juiz](https://github.com/OpenJUIZ/juiz) の Python 版サンプル集です。
`juiz` コマンドと Python 用パッケージは PyPI の [juiz-cli](https://pypi.org/project/juiz-cli/) 0.0.16 に入っているので、`pip install` だけで試せます。Rust や juiz のソースは要りません。

Rust 版のサンプルは [juiz_examples_rust](https://github.com/OpenJUIZ/juiz_examples_rust) にあります。

## しくみ

Python で書いた Process や Container は単体では動きません。`juiz` コマンド (Rust 製) が設定ファイル (`*.conf`) を読み、そこに書かれた Python ファイルを読み込んで実行します。
`pip install juiz-cli` を実行すると、`juiz` コマンドと、Process を書くための Python パッケージ [pyjuiz](https://pypi.org/project/pyjuiz/) (`import juiz`) の両方が入ります。

## 必要なもの

- Python 3.10 以降
- Linux (x86_64 / aarch64)、macOS (Apple Silicon / Intel)、Windows (x86_64) のいずれか

## 1. インストールする

```sh
git clone https://github.com/OpenJUIZ/juiz_examples_python.git
cd juiz_examples_python
python3 -m venv .venv
source .venv/bin/activate        # Windows では .venv\Scripts\activate
pip install -r requirements.txt  # juiz-cli が入る
juiz --help
```

以降の手順は、この venv を有効にしたターミナルで実行してください。
設定ファイルは `./process` などの相対パスで Python ファイルを探すので、**リポジトリのルートで** `juiz` を実行してください。

<details>
<summary>cargo でインストールした juiz を使う場合</summary>

Rust のサンプルも同じ `juiz` で動かしたい場合は、`cargo install juiz_app` で入れた `juiz` を使い、Python 側は `pip install pyjuiz==0.0.16` だけを入れます。
この `juiz` はビルド時に見つけた Python (`python3`) を組み込むので、venv も同じ Python で作ってください (Ubuntu なら `sudo apt install python3-dev python3-venv` も必要です)。
pip の `juiz` は CI でビルドされたものなので、手元でビルドした Rust プラグインは読み込めません (Rust のコンパイラと juiz_sdk の版がそろっていることを起動時に確かめるため)。

</details>

## 2. 動かしてみる

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

API の定義 (OpenAPI) は http://127.0.0.1:8000/api-docs/openapi.json で取得できます。pip 版・crates.io 版の juiz では Swagger UI (`/docs`) は無効になっています。

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
| `requirements.txt` | juiz-cli のバージョン指定 |

## うまく動かないとき

- `ModuleNotFoundError: No module named 'juiz'` や `setup_plugins ... failed` が出る場合は、juiz-cli を入れた venv が有効になっているか確認してください。それでも見つからない場合は `PYTHONPATH` に venv の site-packages を指定してください (例: `export PYTHONPATH=$(python -c 'import site; print(site.getsitepackages()[0])')`)。
- `PyJuizProcessReturnsUnknownTypeError` が出る場合は、Process の関数に戻り値の型ヒント (`-> int` など) が書かれているか確認してください。
- `AttributeError: module '' has no attribute ...` が出る場合は、ファイル名と関数名 (および設定ファイルの名前) がそろっているか確認してください。

## ライセンス

このリポジトリのサンプルは、次のどちらかのライセンスを選んで利用できます(デュアルライセンス)。

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE) または <https://www.apache.org/licenses/LICENSE-2.0>)
- MIT License ([LICENSE-MIT](LICENSE-MIT) または <https://opensource.org/licenses/MIT>)

Licensed under either of Apache License, Version 2.0 or MIT license at your option.

### コントリビューション

明示的に別の意思表示をしない限り、このリポジトリに提出されたコントリビューションは、Apache-2.0 ライセンスの定義に従い、追加の条件なしに上記と同じデュアルライセンスで提供されるものとします。

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions.
