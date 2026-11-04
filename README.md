# juiz_examples_python

ロボット・IoT 向けミドルウェア [juiz](https://github.com/OpenJUIZ/juiz) の Python 版サンプル集です。
`juiz` コマンドと Python 用パッケージは PyPI の [juiz-cli](https://pypi.org/project/juiz-cli/) 0.2.2 に入っているので、`pip install` だけで試せます。Rust や juiz のソースは要りません。

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

Rust のサンプルも同じ `juiz` で動かしたい場合は、`cargo install juiz_app` で入れた `juiz` を使い、Python 側は `pip install pyjuiz==0.2.2` だけを入れます。
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

### データ型: 言語をまたいで同じ型を使う

Process の引数と戻り値に型を付けられます。型は IDL (JIDL) で書き、`juiz idl` で各言語の型を作ります。
このリポジトリの [types/geometry.jidl](types/geometry.jidl) は、Python・[Rust](https://github.com/OpenJUIZ/juiz_examples_rust)・[C++](https://github.com/OpenJUIZ/juiz_examples_cpp)・[Haskell](https://github.com/OpenJUIZ/juiz_examples_haskell) の 4 つのサンプルリポジトリで同じ中身にしてあり、どの言語で作っても型の指紋 (`@sha256:…`) が同じになります。指紋が同じ型どうしは、言語が違ってもそのままつながります (ほかの 3 つのリポジトリには、その言語の Process とこのリポジトリと同じ Python の Process をつなぐ例があります)。

```text
namespace examples.geometry;

record Point2D { double x = 0.0; double y = 0.0; }
record Pose2D  { Point2D position = {"x": 0.0, "y": 0.0}; double theta = 0.0; string frame_id = "map"; }
record Twist2D { double linear = 0.0; double angular = 0.0; }

process Pose2D pose_move(Pose2D pose, Twist2D twist, double dt = 1.0);
```

> データ型は juiz-cli 0.0.23 から使えます。

まず Python の型を `gen/` に作ります。設定ファイルの `option.pythonpath` で `gen/` を読みます。

```sh
juiz idl -g python -o gen types/geometry.jidl
```

型の付いた Process は、作った型を型ヒントに書くだけです ([process/pose_move_python.py](process/pose_move_python.py))。辞書で届いた値も `Pose2D` の値になってから関数に渡り、戻り値は `Pose2D` のまま返せます。

```python
from juiz import juiz_process
from examples.geometry import Point2D, Pose2D, Twist2D

@juiz_process
def pose_move_python(pose: Pose2D = Pose2D(), twist: Twist2D = Twist2D(), dt: float = 1.0) -> Pose2D:
    ...
```

#### 型付きの値をつなぐ: typed_pose.conf

```text
twist0 (twist_python, Twist2D) --Pull--> move0 (pose_move_python) --Push--> print0 (pose_print_python, Pose2D を表示)
```

```sh
juiz -f typed_pose.conf -d
```

別のターミナルから `move0` を実行 (execute) すると、`twist0` から速度を取ってきて動き、結果を `print0` に送ります。

```sh
curl -X PATCH "http://127.0.0.1:8000/api/process/execute?identifier=core://core/process/move0::pose_move_python" -H "Content-Type: application/json" -d '{}'
# => {"frame_id":"map","position":{"x":0.5,"y":0.0},"theta":0.0}
```

```text
pose_move_python: (0.00, 0.00, 0.00) -> (0.50, 0.00, 0.00)
pose_print_python receives Pose2D(x=0.50, y=0.00, theta=0.00, frame_id=map)
```

CLI や curl からは今までどおり辞書で呼べます。書かなかったフィールドは既定値になり、型に合わない値は関数を呼ぶ前にエラーになります。

```sh
juiz process call "http://127.0.0.1:8000/process/move0::pose_move_python" '{"pose": {"position": {"x": 1.0, "y": 2.0}}, "twist": {"linear": 1.0}, "dt": 2.0}' -p
# => CapsulePtr((value:Value({"frame_id":"map","position":{"x":3.0,"y":2.0},"theta":0.0}), option: []))
juiz process call "http://127.0.0.1:8000/process/move0::pose_move_python" '{"pose": {"position": {"x": "a"}}, "twist": {}, "dt": 1.0}' -p
# => ... ValueDoesNotMatchTypeError: value does not match type double at 'pose.position.x': expected a number, found "a"
```

JIDL の `process pose_move(...)` からは、型付きで呼び出すクライアント `PoseMoveClient` も作られます ([scripts/pose_client.py](scripts/pose_client.py))。引数も戻り値も `Pose2D` で受け渡せます。名前で探すので、ほかの言語のサンプルの `pose_move` も同じように呼べます。

```python
from examples.geometry import Point2D, Pose2D, PoseMoveClient, Twist2D

move = PoseMoveClient.connect("move0")
moved = move(Pose2D(position=Point2D(x=1.0, y=2.0)), Twist2D(linear=1.0), dt=2.0)
```

```sh
python scripts/pose_client.py
# Pose2D: x=3.00 y=2.00 theta=0.00 frame_id=map
# dt omitted: x=2.00
```

読み込んだ型は `juiz type` で見られます。

```sh
juiz type list
# => ["examples.geometry.Point2D@sha256:5649ab39…","examples.geometry.Pose2D@sha256:123b8c15…","examples.geometry.Twist2D@sha256:115b9e0f…"]
juiz type show examples.geometry.Pose2D
# // examples.geometry.Pose2D@sha256:123b8c15…
# // used by: pose_move_python, pose_print_python
# namespace examples.geometry;
# ...
```

#### 型が合わないとつながらない: typed_mismatch.conf

`twist0` の `Twist2D` を `move0` の引数 `pose` (`Pose2D`) につなごうとする設定ファイルです。juiz は接続を作らず、エラーで終わります。

```sh
juiz -f typed_mismatch.conf -d
# Error:setup_objects() failed in setup in system.rs
# ...
#     2: Type examples.geometry.Twist2D@sha256:115b9e0f… cannot be read as examples.geometry.Pose2D@sha256:123b8c15… at 'Pose2D': record name examples.geometry.Twist2D does not match examples.geometry.Pose2D (add an alias to read it)
```

### Transformations: 部品の位置関係を木にする

ロボットの部品 (台車・雲台・カメラ) を Container にし、部品同士のつながり (Transform) と基点 (Anchor) を設定ファイルに書くと、juiz が各部品の位置姿勢 (ContainerPose) を計算します。

> juiz 0.2.0 から使える機能です。

`transformations.conf` の木は次のとおりです。`map` と `odom` は juiz に組み込みの Anchor で、プラグインは要りません。

```text
map (PeriodicExecutionAnchor, 10 Hz)        … 10 Hz で木をたどって位置姿勢を計算し直す
└─ odom (StaticAnchor)                      … 書き込みがあったときだけ計算し直す。map から (1, 2, 0) ずれている
   └─ base0 (台車 mobile_base_python)        … move0 がオドメトリを set_pose で書く
      └─ pantilt0 (雲台 pantilt_python)      … 台車の (0.1, 0, 0.3) に付く。pan0 がパン角を書く
         └─ camera0 (カメラ camera_python)   … 雲台の (0.05, 0, 0.02) に付く。Transform だけ
```

部品は `component/mobile_robot_python.py` の 1 つの Component です。ContainerProcess の中では `juiz.pose(obj, "map")` で読み、`juiz.set_pose(obj, "odom", pose)` で書きます (`obj` は ContainerProcess の第 1 引数)。`set_pose` は親 → 自分の Transform を書き換えるので、子の雲台・カメラも一緒に動きます。

```python
from juiz import juiz_container_process, set_pose
from juiz_std.geometry import Point3D, Pose, PoseStamped

@juiz_container_process(container_type="mobile_base_python")
def mobile_base_python_move(base, vx: float = 0.0, omega: float = 0.0, dt: float = 1.0,
                            reference: str = "odom") -> PoseStamped:
    base.x += vx * math.cos(base.theta) * dt
    base.y += vx * math.sin(base.theta) * dt
    base.theta += omega * dt
    p = Pose(position=Point3D(x=base.x, y=base.y, z=0.0), orientation=yaw_quaternion(base.theta))
    return set_pose(base, reference, p)
```

また `pose_listeners:` で、台車の位置姿勢が書かれたら Process `print0` (`pose_print_python`、引数は `juiz_std.geometry.PoseStamped`) を呼ぶ Pose 通知を登録しています。

```sh
juiz -f transformations.conf -d
```

別の端末で台車を動かし、雲台を 90 度回します。

```sh
juiz container-process call "http://127.0.0.1:8000/container_process/move0::mobile_base_python_move:base0" '{"vx": 1.0, "dt": 1.0}' -p
# => CapsulePtr((value:Value({"header":{"frame_id":"odom",...},"pose":{"orientation":{...},"position":{"x":1.0,"y":0.0,"z":0.0}}}), option: []))
juiz container-process call "http://127.0.0.1:8000/container_process/pan0::pantilt_python_set_pan:pantilt0" '{"pan": 1.5707963267948966}' -p
```

1 つ目の呼び出しで、juiz を起動した端末に Pose 通知の出力が出ます。

```text
pose_print_python: x=1.00 y=0.00 yaw=0.0deg (from odom)
```

カメラの位置姿勢を読みます。雲台が回ったので、カメラは台車の左 (y = 0.05) に来ています。`map` から見ると `map` → `odom` のずれ (1, 2, 0) が足されます。

```sh
juiz container pose camera0 --reference odom
# => position: x=1.1, y=0.05, z=0.32 (JSON の PoseStamped)
juiz container pose camera0 --reference map
# => position: x=2.1, y=2.05, z=0.32
juiz container-process call "http://127.0.0.1:8000/container_process/camera_pose0::camera_python_pose:camera0" '{"reference": "map"}' -p
juiz anchor tree map
# map  position (0, 0, 0)  orientation (0, 0, 0, 1)
# └─ odom  position (1, 2, 0)  orientation (0, 0, 0, 1)
#    └─ base0  position (2, 2, 0)  orientation (0, 0, 0, 1)
#       └─ pantilt0  position (2.1, 2, 0.3)  orientation (0, 0, 0.7071067811865475, 0.7071067811865476)
#          └─ camera0  position (2.1, 2.05, 0.32)  orientation (0, 0, 0.7071067811865475, 0.7071067811865476)
```

`map` は Periodic なので、書き込みの直後に読むと最大 1 周期 (0.1 秒) 古い値が返ります。`odom` は Static なので、`set_pose` が戻った時点で新しい値になっています。
管理画面 (`http://127.0.0.1:8000/ui`) の「変換木」でも木と位置姿勢を見られます。

#### 読むだけの ContainerProcess: readonly

カメラの `camera_python_pose` は位置姿勢を読むだけなので、`readonly=True` を付けて readonly の ContainerProcess にしています。

```python
@juiz_container_process(container_type="camera_python", readonly=True)
def camera_python_pose(camera, reference: str = "map") -> PoseStamped:
    """基準 reference から見た自分の位置姿勢"""
    return pose(camera, reference)
```

juiz は readonly の ContainerProcess を Container の読み出しロックで呼ぶので、同じ Container の readonly 同士は並行に走ります (readonly でないものとは順番に走ります)。readonly の中で `set_pose` を呼ぶと `PoseNotWritableError` になります。Python では Container のオブジェクト自体の書き換えは止められないので、readonly の中では読むだけにしてください。
readonly かどうかは ContainerProcess の情報 (HTTP の API) に出ます。

```sh
curl "http://127.0.0.1:8000/api/container_process/profile_full?identifier=core://core/container_process/camera_pose0::camera_python_pose:camera0"
# => {..."readonly":true,...}
```

> juiz 0.2.2 から使える機能です。

#### System をまたぐ: transformations_map.conf と transformations_robot.conf

上の木を、地図の System とロボットの System の 2 つに分けた版です。地図 (`map`) を持つ System と、台車・雲台・カメラを持つ System を別のプロセスで動かし、ロボットの System から `map` を基準に読めます。

> juiz 0.2.1 から使える機能です。

```text
地図の System (transformations_map.conf、ポート 8000)
map (PeriodicExecutionAnchor, 10 Hz)
 ┊  map → odom の Transform はロボットの System が持ち、map の位置を取りに来る (写し)
ロボットの System (transformations_robot.conf、ポート 8001)
└─ odom (StaticAnchor) → base0 (台車) → pantilt0 (雲台) → camera0 (カメラ)
```

`map → odom` の Transform は、子の `odom` を持つロボットの System の設定ファイルに書きます。始点は地図の System の `map` をブローカー付きの ID で書き、取りに行く頻度 `rate` (Hz) と、つながらないときに写しを消すまでの `timeout` (秒) を付けます。地図の System の設定ファイルには `map` を置くだけです。

```yaml
# transformations_robot.conf (抜粋)
transforms:
  - source: http://127.0.0.1:8000/container/map::periodic_anchor
    destination: odom
    translation: {x: 1.0, y: 2.0, z: 0.0}
    rate: 10.0
    timeout: 3.0
```

2 つの端末で、地図の System、ロボットの System の順に起動します (逆の順でも、地図の System が起動した時点で取り込みが始まります)。

```sh
juiz -f transformations_map.conf -d
juiz -f transformations_robot.conf -d
```

別の端末で、上と同じく台車を動かし雲台を回します (ロボットの System はポート 8001)。

```sh
juiz container-process call "http://127.0.0.1:8001/container_process/move0::mobile_base_python_move:base0" '{"vx": 1.0, "dt": 1.0}' -p
juiz container-process call "http://127.0.0.1:8001/container_process/pan0::pantilt_python_set_pan:pantilt0" '{"pan": 1.5707963267948966}' -p
```

ロボットの System には `map` がありませんが、名前 `map` は地図の System の `map` の写しに解決します。基準 (`frame_id`) は写しの ID です。

```sh
juiz -s http://127.0.0.1:8001 container pose camera0 --reference map
# => position: x=2.1, y=2.05, z=0.32、frame_id: http://127.0.0.1:8000/container/map::periodic_anchor
juiz -s http://127.0.0.1:8001 transform list --long
# http://127.0.0.1:8000/container/map::periodic_anchor -> core://core/container/odom::static_anchor  translation (1, 2, 0)  rotation (0, 0, 0, 1)  (remote: ok)
# ...
juiz -s http://127.0.0.1:8001 anchor tree map
# map  position (0, 0, 0)  orientation (0, 0, 0, 1)
# └─ odom  position (1, 2, 0)  orientation (0, 0, 0, 1)
#    └─ ...
```

地図の System からも、ロボットの System の Container を ID で指定すれば `map` から見て読めます (ロボットの System に回ります)。地図の System の木にはロボットの部品は入らず、`map` に「取りに来ている System がある」印だけが付きます。

```sh
juiz container pose "http://127.0.0.1:8001/container/camera0::camera_python" --reference map
# => position: x=2.1, y=2.05, z=0.32、frame_id: map
juiz container list --long
# /          map   periodic_anchor  http://127.0.0.1:8000/container/map::periodic_anchor
#     anchor: periodic (10 Hz)
#     remote child: <ロボットの System の UUID> -> core://core/container/odom::static_anchor
```

地図の System を止めると、ロボットの System は `timeout` (3 秒) の後に写しを消し、`transform list --long` が `(remote: lost)` になります。`map` を基準に読むと「つながらない」エラーになりますが、`odom` を基準にした読み書きはそのまま続けられます。地図の System を起動し直すと、自動で写しが戻ります。
管理画面 (`http://127.0.0.1:8001/ui`) の「変換木」では、写しが破線と「写し」の印で表示されます。

### アプリを .juizapp で配る

`packages/` の下のアプリを、1 つのファイル (`.juizapp`、zip) にまとめて配れます (juiz 0.0.28 から)。受け取った人はサンプル集をクローンしなくても、`juiz run` だけで動かせます。

```sh
python scripts/make_packages.py
# Packed talker_listener 0.1.0 (any; 5 files) into .../dist/talker_listener-0.1.0.juizapp
# Packed chatter_base 0.1.0 (any; 4 files) into .../dist/chatter_base-0.1.0.juizapp
# Packed chatter_listener 0.1.0 (any; 4 files) into .../dist/chatter_listener-0.1.0.juizapp
```

`packages/<名前>/` に置くのはマニフェスト `juizapp.yaml` と設定ファイル `app.conf` だけで、`scripts/make_packages.py` が Process の `.py` を `process/` から写してから `juiz pack` を呼びます。Python だけのパッケージなので、どの OS で作っても同じものになり、どの OS でも動きます。
タグ (`v*`) を付けると、CI が作った `.juizapp` を [Releases](https://github.com/OpenJUIZ/juiz_examples_python/releases) に載せます。

ファイルを渡すと、展開してそのまま起動します (talker_listener.conf と同じ動き)。

```sh
juiz run dist/talker_listener-0.1.0.juizapp
# listener_python receives "Hello, World!"
```

#### 基礎パッケージとアプリ: chatter_base / chatter_listener

常駐させる側を基礎パッケージ (`kind: base`)、それを使う側をアプリとして分けて配る例です。

- `chatter_base`: `talker0` が 1 秒ごとに Topic `chatter` へ `"Hello from chatter_base"` を publish する。IPC 名 `chatter_base` と HTTP の 8100 番 (`base.http_port`) で待ち受ける
- `chatter_listener`: `depends: {chatter_base: ">=0.1, <0.2"}`。`listener0` が Topic `chatter` を受け取って表示する

インストールしておくと、名前で起動できます。

```sh
juiz install dist/chatter_base-0.1.0.juizapp
juiz install dist/chatter_listener-0.1.0.juizapp
juiz packages
# NAME              VERSION  KIND
# chatter_base      0.1.0    base
# chatter_listener  0.1.0    app

juiz run chatter_base              # ターミナル 1
juiz run chatter_listener          # ターミナル 2
# listener_python receives "Hello from chatter_base"
```

アプリは起動するときに `ipc://chatter_base` へ subsystem としてつなぎ、相手が chatter_base の 0.1 系であることを確かめます。基礎を起動していなければ、`juiz run chatter_base` で先に起動するよう案内して止まります。
別の機械で動いている基礎を使うときは、`juiz run chatter_listener --depend chatter_base=http://192.168.0.10:8100` のように接続先を指定します。

## 構成

| パス | 内容 |
| --- | --- |
| `process/` | Process (入力と出力を持つ冪等な関数) のサンプル |
| `container/` | Container (状態を持つ) と ContainerProcess のサンプル |
| `component/` | 複数の要素を 1 つのファイルにまとめた Component のサンプル (`mobile_robot_python.py` は Transformations の部品) |
| `types/` | 4 つのサンプルリポジトリで共通に使う型 (JIDL) |
| `images/` | 画像処理のサンプル (`image_pipeline.conf`) が読み込む画像 |
| `scripts/time_image_pipeline.py` | `image_pipeline.conf` の Composite 版と接続版の時間を測るスクリプト |
| `scripts/pose_client.py` | 生成した client stub (`PoseMoveClient`) で `typed_pose.conf` の `move0` を呼ぶスクリプト |
| `*.conf` | 各サンプルを動かすための juiz の設定ファイル |
| `packages/` | `.juizapp` にするアプリのマニフェストと設定ファイル |
| `scripts/make_packages.py` | `packages/` のアプリを `dist/` に `.juizapp` にするスクリプト |
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
