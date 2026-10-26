# juiz_examples_python

ロボット・IoT 向けミドルウェア [juiz](https://github.com/OpenJUIZ/juiz) の Python 版サンプル集です。
`juiz` コマンドと Python 用パッケージは PyPI の [juiz-cli](https://pypi.org/project/juiz-cli/) 0.0.21 に入っているので、`pip install` だけで試せます。Rust や juiz のソースは要りません。

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

Rust のサンプルも同じ `juiz` で動かしたい場合は、`cargo install juiz_app` で入れた `juiz` を使い、Python 側は `pip install pyjuiz==0.0.21` だけを入れます。
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

Swagger UI は http://127.0.0.1:8000/docs/ で開けます。API の定義 (OpenAPI) は http://127.0.0.1:8000/api-docs/openapi.json で取得できます。

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

### ネームスペース: 同じ構成を並べて動かす

ネームスペースを使うと、同じ名前の Process を 1 つの System に並べて置けます。ID はクラスの後ろ・名前の前にネームスペースが入った `http://127.0.0.1:8000/process/robot1/talker0::talker_python` の形になります。

#### 1 つの設定ファイルで 2 台分を置く: namespace.conf

`talker0` と `listener0` を `robot1` と `robot2` の 2 つのネームスペースに置き、Topic `chatter` でつなぎます。Topic 名もネームスペースの中で解決される (`robot1/chatter` と `robot2/chatter`) ので、それぞれの `listener0` には同じネームスペースの `talker0` の出力だけが届きます。

```sh
juiz -f namespace.conf -d
# talker_python says "Hello from robot1"
# listener_python receives "Hello from robot1"
# talker_python says "Hello from robot2"
# listener_python receives "Hello from robot2"
# ...
```

別のターミナルから、ネームスペースの列つきで一覧を出したり、ネームスペース付きの ID で呼び出したりできます。

```sh
juiz process list --long
# NAMESPACE  NAME       TYPE           ID
# /robot1    talker0    talker_python  http://127.0.0.1:8000/process/robot1/talker0::talker_python
# ...
juiz process call "http://127.0.0.1:8000/process/robot1/talker0::talker_python" '{"message": "Hi"}' -p
# => CapsulePtr((value:Value("Hi"), option: []))
```

設定ファイルでは各要素に `namespace` を書きます (`/` で始めるとルートからの絶対指定)。トップレベルに `namespace` を書くと、全体の既定のネームスペースになります。

#### 同じ設定ファイルを 2 つ起動する: --namespace

`--namespace` を付けると、設定ファイルの既定のネームスペースを置き換えて起動できます。2 つのターミナルで次のように起動すると、2 つ目は 1 つ目のサブシステムになり (8001 番ポートで待ち受け)、1 つの System として扱えます。

```sh
juiz -f increment_process.conf --namespace robot1 -d
```

```sh
juiz -f increment_process.conf --namespace robot2 -d
```

```sh
juiz process list --namespace robot2
# => ["http://127.0.0.1:8001/process/robot2/increment0::increment_process_python"]
juiz process call "http://127.0.0.1:8000/process/robot1/increment0::increment_process_python" '{"arg1": 1}' -p
# => CapsulePtr((value:Value(2), option: []))
juiz process call "http://127.0.0.1:8001/process/robot2/increment0::increment_process_python" '{"arg1": 10}' -p
# => CapsulePtr((value:Value(11), option: []))
```

### Composition: 画像処理の段を 1 つの Process にまとめる

画像を読み込み → 縮小 → 二値化して、白い画素の割合を返す処理を、4 つの Process で書きました ([process/](process/) の `image_*_python.py`)。

```python
@juiz_process
def image_resize_python(img: Image, width: int = 320, height: int = 240) -> Image:
    return img.resize((width, height))
```

[image_pipeline.conf](image_pipeline.conf) では、この 4 段を 2 通りに組んでいます。

1. **Composite**: `composites:` に式の木を書き、4 段を 1 つの Process の型 `image_pipeline_python` にまとめる。インスタンス `pipeline0` は普通の Process と同じように呼べる。
2. **接続**: 4 段を別々の Process (`load0` → `resize0` → `binarize0` → `ratio0`) として置き、Pull 接続でつなぐ。

```yaml
composites:
  - type_name: image_pipeline_python
    body:
      process: image_white_ratio_python
      args:
        img:
          process: image_binarize_python
          args:
            img:
              process: image_resize_python
              args:
                img:
                  process: image_load_python
```

`args` に書かなかった引数 (`path`、`width`、`height`、`threshold`) は、元の名前のまま Composite の引数になります。

```sh
juiz -f image_pipeline.conf -d
```

別のターミナルから、Composite は引数を全部渡して `call` します。

```sh
juiz process call "http://127.0.0.1:8000/process/pipeline0::image_pipeline_python" '{"path": "images/sample.png", "width": 320, "height": 240, "threshold": 128}' -p
# => CapsulePtr((value:Value(0.2810286458333333), option: []))
juiz process list --long   # pipeline0 の下に式の木が出る
```

接続版は、末端の `ratio0` を `execute` すると、上流の `binarize0` → `resize0` → `load0` から値が集まります (CLI にはまだ execute がないので HTTP の API を呼びます)。各段の引数は既定値のままです。

```sh
curl -X PATCH "http://127.0.0.1:8000/api/process/execute?identifier=http://127.0.0.1:8000/process/ratio0::image_white_ratio_python" -H "Content-Type: application/json" -d "{}"
# => 0.2810286458333333
```

#### どちらを使うか

| | Composite | 接続 |
| --- | --- | --- |
| 外から見える形 | 1 つの Process。引数は全段の引数をまとめたもの | 段ごとの Process |
| 呼び方 | `call` に引数を渡すだけ | 末端を `execute` する。各段の引数は段ごとに設定する |
| 途中の段 | 外からは呼べない (インスタンスを作らない) | 1 段ずつ呼んだり、出力を別の Process に配ったりできる |
| 向いている使い方 | 決まった前処理をひとまとめにして、サーバーのように呼び出す | 実行コンテキストで周期的に回す、途中の結果を複数の Process で使う、別プロセスの juiz とつなぐ |

#### 時間を測る

`juiz -f image_pipeline.conf -d` を起動したまま、[scripts/time_image_pipeline.py](scripts/time_image_pipeline.py) を実行すると、Composite 版と接続版を何度か呼んで 1 回あたりの時間を出します。比べるために、同じ 4 つの関数を juiz を通さずに Python だけでつないだ時間も出します。

```sh
python scripts/time_image_pipeline.py 20
```

今の juiz では、Python の段の間で画像を受け渡すたびに Python と juiz (Rust) の間で画像を変換するので、Composite 版も接続版もほぼ同じ時間で、Python だけの場合よりかなり遅くなります。
Python 同士の段の間で変換を省く遅延評価 ([OpenJUIZ/juiz#3](https://github.com/OpenJUIZ/juiz/issues/3)) が入ると、Composite 版の時間が Python だけの場合に近づくはずです。

## 構成

| パス | 内容 |
| --- | --- |
| `process/` | Process (入力と出力を持つ冪等な関数) のサンプル |
| `container/` | Container (状態を持つ) と ContainerProcess のサンプル |
| `component/` | 複数の要素を 1 つのファイルにまとめた Component のサンプル |
| `images/` | 画像処理のサンプル (`image_pipeline.conf`) が読み込む画像 |
| `scripts/time_image_pipeline.py` | `image_pipeline.conf` の Composite 版と接続版の時間を測るスクリプト |
| `*.conf` | 各サンプルを動かすための juiz の設定ファイル |
| `requirements.txt` | juiz-cli のバージョン指定 |
| `tests/test_examples.py` | 上のサンプルを起動して呼び出し、結果を確かめるテスト (`python tests/test_examples.py`)。CI でも実行する |

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
