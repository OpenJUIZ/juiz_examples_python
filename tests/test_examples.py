"""README のサンプルを実際に動かして結果を確かめるテスト。

juiz-cli をインストールした環境で、リポジトリのルートから実行する:

    python tests/test_examples.py

各サンプルごとに `juiz -f <conf> -d` を起動し、README と同じ呼び出しを行って
出力に期待する値が含まれるかを確かめたあと、Ctrl+C(SIGINT)で止める。
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8000
BASE = f"http://127.0.0.1:{PORT}"

# 呼び出しの代わりに (EXECUTE, ID) と書くと、HTTP の /api/process/execute を呼ぶ
EXECUTE = "execute"
# 呼び出しの代わりに (SCRIPT, パス) と書くと、その Python のスクリプトを実行する
SCRIPT = "script"


class Fails(str):
    """期待する出力を Fails("...") と書くと、呼び出しがエラーになり、出力にその文字列が含まれることを確かめる。

    juiz の CLI は呼び出しがエラーでも終了コード 0 で終わるので、出力の "Error" で見分ける。
    """

# サンプル共通の型 (types/geometry.jidl) の識別子。4 つのサンプルリポジトリで同じになる
# (言語をまたいでつながる) ことを確かめるため、指紋をここに書いておく。types/geometry.jidl を変えたら
# 4 つのリポジトリの types/geometry.jidl とこの値をそろえる
POSE2D_ID = "examples.geometry.Pose2D@sha256:123b8c15cda217478b331e2133a5de7c5aafb8075d0ca203e8a7e7e50797cf9b"
TWIST2D_ID = "examples.geometry.Twist2D@sha256:115b9e0f7b27c487a3af04922d19364cc387e3116468e90f22034c4f51a9fe71"

# (設定ファイル, [(juiz のサブコマンドと引数, 出力に含まれるべき文字列)], サーバーの出力に含まれるべき文字列)
CASES = [
    ("increment_process.conf", [
        (["process", "call", f"{BASE}/process/increment0::increment_process_python", '{"arg1": 3}', "-p"], "Value(4)"),
    ], None),
    ("decrement_process.conf", [
        (["process", "call", f"{BASE}/process/decrement0::decrement_process_python", '{"arg1": 3}', "-p"], "Value(2)"),
    ], None),
    ("talker_listener.conf", [], 'listener_python receives "Hello, World!"'),
    ("example_container.conf", [
        (["container-process", "call",
          f"{BASE}/container_process/increment0::example_container_python_increment:container0",
          '{"arg1": 5}', "-p"], "Value(5)"),
        (["container-process", "call",
          f"{BASE}/container_process/increment0::example_container_python_increment:container0",
          '{"arg1": 5}', "-p"], "Value(10)"),
        (["container-process", "call",
          f"{BASE}/container_process/get0::example_container_python_get:container0", "{}", "-p"], "Value(10)"),
    ], None),
    ("example_component.conf", [
        (["process", "call", f"{BASE}/process/increment0::example_component_python_increment", '{"arg1": 1}', "-p"],
         "Value(2)"),
        (["container-process", "call",
          f"{BASE}/container_process/set0::example_component_python_container_set:container0",
          '{"value": 7}', "-p"], ""),
        (["container-process", "call",
          f"{BASE}/container_process/get0::example_component_python_container_get:container0", "{}", "-p"],
         "Value(7)"),
    ], None),
    # 同じ名前の talker0 / listener0 を robot1 と robot2 に置く。Topic もネームスペースごとに分かれる
    ("namespace.conf", [
        (["process", "call", f"{BASE}/process/robot1/talker0::talker_python", '{"message": "Hi"}', "-p"],
         "Value(\"Hi\")"),
    ], ['listener_python receives "Hello from robot1"', 'listener_python receives "Hello from robot2"']),
    # 同じ画像処理を Composite (pipeline0) と Pull 接続 (ratio0) で組み、同じ結果になること
    ("image_pipeline.conf", [
        (["process", "call", f"{BASE}/process/pipeline0::image_pipeline_python",
          '{"path": "images/sample.png", "width": 320, "height": 240, "threshold": 128}', "-p"], "Value(0.281"),
        (["process", "call", f"{BASE}/process/pipeline0::image_pipeline_python",
          '{"path": "images/sample.png", "width": 320, "height": 240, "threshold": 200}', "-p"],
         "Value(0.146"),
        # 接続をたどって上流から値を集めるのは execute (CLI にはないので HTTP の API を直接呼ぶ)
        ((EXECUTE, f"{BASE}/process/ratio0::image_white_ratio_python"), "0.281"),
    ], None),
    # サンプル共通の型 (types/geometry.jidl)。twist0 の Twist2D を move0 が受け、move0 の Pose2D を print0 が受ける
    ("typed_pose.conf", [
        # execute は twist0 から速度 (linear=0.5) を取ってきて動き、結果を print0 に Push する
        ((EXECUTE, f"{BASE}/process/move0::pose_move_python"), '"position":{"x":0.5,"y":0.0}'),
        # 型付きの引数も CLI からは辞書で渡せる。書かなかったフィールドは既定値になる
        (["process", "call", f"{BASE}/process/move0::pose_move_python",
          '{"pose": {"position": {"x": 1.0, "y": 2.0}}, "twist": {"linear": 1.0}, "dt": 2.0}', "-p"],
         '"position":{"x":3.0,"y":2.0}'),
        # 型に合わない辞書は、関数を呼ぶ前にエラーになる (エラーに場所 pose.position.x が付く)
        (["process", "call", f"{BASE}/process/move0::pose_move_python",
          '{"pose": {"position": {"x": "a"}}, "twist": {}, "dt": 1.0}', "-p"], Fails("pose.position.x")),
        # 生成した client stub (PoseMoveClient) は Pose2D で受け取る
        ((SCRIPT, "scripts/pose_client.py"), "Pose2D: x=3.00 y=2.00 theta=0.00 frame_id=map"),
        (["type", "list"], POSE2D_ID),
        (["type", "list"], TWIST2D_ID),
        (["type", "show", "examples.geometry.Pose2D"], "used by: pose_move_python, pose_print_python"),
    ], "pose_print_python receives Pose2D(x=0.50, y=0.00, theta=0.00, frame_id=map)"),
]

# 型の合わない接続 (Twist2D を Pose2D の引数へ) を書いた設定ファイル。juiz は起動せずにエラーで終わる
MISMATCH_CONF = "typed_mismatch.conf"
MISMATCH_ERROR = f"{TWIST2D_ID} cannot be read as {POSE2D_ID}"


def run_call(juiz: str, args) -> tuple[int, str, str]:
    """1 つの呼び出しを行い、(終了コード, 標準出力, 標準エラー) を返す。"""
    if isinstance(args, tuple) and args[0] == EXECUTE:
        url = f"{BASE}/api/process/execute?" + urllib.parse.urlencode({"identifier": args[1]})
        request = urllib.request.Request(url, data=b"{}", method="PATCH",
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return 0, response.read().decode("utf-8"), ""
        except OSError as e:
            return 1, "", str(e)
    if isinstance(args, tuple) and args[0] == SCRIPT:
        result = subprocess.run([sys.executable, args[1]], cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=30)
        return result.returncode, result.stdout, result.stderr
    # juiz の出力は UTF-8 (Windows の既定の cp1252 では日本語のエラーメッセージを読めない)
    result = subprocess.run([juiz, *args], cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=30)
    return result.returncode, result.stdout, result.stderr


def wait_for_port(port: int, timeout: float, server: subprocess.Popen) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"juiz が終了しました (終了コード {server.returncode})")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise TimeoutError(f"juiz が {timeout} 秒以内にポート {port} で待ち受けを始めませんでした")


def wait_for_port_free(port: int, timeout: float) -> None:
    """前の juiz が使っていたポートを再び待ち受けられるようになるまで待つ。"""
    deadline = time.monotonic() + timeout
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # HTTP の API を直接呼ぶとサーバー側に TIME_WAIT が残る。juiz と同じく SO_REUSEADDR を付けて確かめる
                # (Windows の SO_REUSEADDR は意味が違い、TIME_WAIT で bind が止まることもないので付けない)
                if os.name != "nt":
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                return
        except OSError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)


def wait_for_output(path: str, expected: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with open(path, encoding="utf-8", errors="replace") as f:
            if expected in f.read():
                return True
        time.sleep(0.5)
    return False


def generate_python_types(juiz: str) -> bool:
    """README の手順どおり、データ型のサンプルの Python の型を gen/ に作る。"""
    print("--- juiz idl -g python -o gen types/geometry.jidl", flush=True)
    result = subprocess.run([juiz, "idl", "-g", "python", "-o", "gen", "types/geometry.jidl"], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if result.returncode != 0:
        print(f"NG: juiz idl が失敗しました\n{result.stdout}{result.stderr}", file=sys.stderr)
        return False
    return True


def run_mismatch(juiz: str) -> bool:
    """型の合わない接続を書いた設定ファイルでは、juiz がエラーで終わること。"""
    print(f"--- {MISMATCH_CONF}", flush=True)
    wait_for_port_free(PORT, 30)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        result = subprocess.run([juiz, "-f", MISMATCH_CONF, "-d"], cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=env, timeout=60)
    except subprocess.TimeoutExpired:
        print("NG: 型の合わない接続なのに juiz が起動したままです", file=sys.stderr)
        return False
    output = result.stdout + result.stderr
    if result.returncode == 0 or MISMATCH_ERROR not in output:
        print(f"NG: 型が合わないエラーになりませんでした (終了コード {result.returncode})\n{output}",
              file=sys.stderr)
        return False
    print(f"  {MISMATCH_ERROR}", flush=True)
    return True


def run_case(juiz: str, conf: str, calls: list, expected_output: str | list[str] | None) -> bool:
    print(f"--- {conf}", flush=True)
    wait_for_port_free(PORT, 30)
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    with tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False) as log:
        log_path = log.name
        # 出力をファイルに書くと Python の print がバッファされて終了まで出てこないので、バッファを切る
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        server = subprocess.Popen([juiz, "-f", conf, "-d"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                  env=env, **kwargs)
    ok = True
    try:
        wait_for_port(PORT, 60, server)
        for args, expected in calls:
            returncode, stdout, stderr = run_call(juiz, args)
            print(f"juiz {' '.join(args)}\n  {stdout.strip()}", flush=True)
            if isinstance(expected, Fails):
                if "Error" not in stdout + stderr or expected not in stdout + stderr:
                    print(f"NG: 失敗して {str(expected)!r} を出すはずでした\n{stderr}", file=sys.stderr)
                    ok = False
                    break
                continue
            if returncode != 0 or expected not in stdout:
                print(f"NG: {expected!r} が出力に含まれていません\n{stderr}", file=sys.stderr)
                ok = False
                break
        if isinstance(expected_output, str):
            expected_output = [expected_output]
        for expected in expected_output or []:
            if ok and not wait_for_output(log_path, expected, 15):
                print(f"NG: juiz の出力に {expected!r} が含まれていません", file=sys.stderr)
                ok = False

        server.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            print("NG: Ctrl+C で juiz が止まりませんでした", file=sys.stderr)
            ok = False
    except Exception as e:
        print(f"NG: {e}", file=sys.stderr)
        ok = False
    finally:
        if server.poll() is None:
            server.kill()
            server.wait()
        if not ok:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                print(f"juiz の出力:\n{f.read()}", file=sys.stderr)
        os.unlink(log_path)
    return ok


def start_server(juiz: str, args: list, log) -> subprocess.Popen:
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    return subprocess.Popen([juiz, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, env=env, **kwargs)


def stop_server(server: subprocess.Popen) -> bool:
    server.send_signal(signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT)
    try:
        server.wait(timeout=15)
        return True
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait()
        print("NG: Ctrl+C で juiz が止まりませんでした", file=sys.stderr)
        return False


def run_two_namespaces(juiz: str) -> bool:
    """README の「同じ設定ファイルを 2 つ起動する」の手順。

    increment_process.conf を --namespace robot1 と robot2 で起動し、2 つ目は 1 つ目のサブシステムになる。
    """
    print("--- increment_process.conf --namespace robot1 / robot2", flush=True)
    wait_for_port_free(PORT, 30)
    wait_for_port_free(PORT + 1, 30)
    r1 = f"{BASE}/process/robot1/increment0::increment_process_python"
    r2 = f"http://127.0.0.1:{PORT + 1}/process/robot2/increment0::increment_process_python"
    servers = []
    logs = []
    ok = True
    try:
        for i, ns in enumerate(["robot1", "robot2"]):
            log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
            logs.append(log.name)
            servers.append(start_server(juiz, ["-f", "increment_process.conf", "--namespace", ns, "-d"], log))
            log.close()
            wait_for_port(PORT + i, 60, servers[i])
        # 2 つ目の登録の手続き中に問い合わせると互いの応答待ちで止まることがある (juiz#159) ので少し待つ
        time.sleep(3)
        calls = [
            (["process", "list", "--namespace", "robot2"], r2),
            (["process", "call", r1, '{"arg1": 1}', "-p"], "Value(2)"),
            (["process", "call", r2, '{"arg1": 10}', "-p"], "Value(11)"),
        ]
        for args, expected in calls:
            # juiz の出力は UTF-8 (Windows の既定の cp1252 では日本語のエラーメッセージを読めない)
            result = subprocess.run([juiz, *args], cwd=ROOT, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=60)
            print(f"juiz {' '.join(args)}\n  {result.stdout.strip()}", flush=True)
            if result.returncode != 0 or expected not in result.stdout:
                print(f"NG: {expected!r} が出力に含まれていません\n{result.stderr}", file=sys.stderr)
                ok = False
                break
    except Exception as e:
        print(f"NG: {e}", file=sys.stderr)
        ok = False
    finally:
        for server in reversed(servers):
            if server.poll() is None and not stop_server(server):
                ok = False
        for path in logs:
            if not ok:
                with open(path, encoding="utf-8", errors="replace") as f:
                    print(f"juiz の出力:\n{f.read()}", file=sys.stderr)
            os.unlink(path)
    return ok


def run_packages(juiz: str) -> bool:
    """README の「.juizapp で配る」の手順。

    scripts/make_packages.py で dist/ に .juizapp を作り、talker_listener をファイルから juiz run する。
    基礎 chatter_base とアプリ chatter_listener は juiz install してから名前で juiz run し、
    アプリが基礎の Topic chatter を受け取ること。インストール先は一時ディレクトリにする。
    """
    print("--- scripts/make_packages.py / juiz run / juiz install", flush=True)
    result = subprocess.run([sys.executable, "scripts/make_packages.py"], cwd=ROOT, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=120)
    print(result.stdout.strip(), flush=True)
    if result.returncode != 0:
        print(f"NG: .juizapp を作れませんでした\n{result.stderr}", file=sys.stderr)
        return False
    data_dir = tempfile.mkdtemp(prefix="juiz_data_")
    saved = {k: os.environ.get(k) for k in ["JUIZ_DATA_DIR", "JUIZ_CACHE_DIR"]}
    os.environ["JUIZ_DATA_DIR"] = os.path.join(data_dir, "data")
    os.environ["JUIZ_CACHE_DIR"] = os.path.join(data_dir, "cache")
    servers = []
    logs = []
    ok = True

    def start(args: list, expected: str) -> bool:
        log = tempfile.NamedTemporaryFile("w+", suffix=".log", delete=False)
        logs.append(log.name)
        servers.append(start_server(juiz, args, log))
        log.close()
        if wait_for_output(log.name, expected, 60):
            print(f"juiz {' '.join(args)}\n  {expected}", flush=True)
            return True
        print(f"NG: juiz の出力に {expected!r} が含まれていません", file=sys.stderr)
        return False

    try:
        # ファイルを渡すと、展開してそのまま起動する
        wait_for_port_free(PORT, 30)
        ok = start(["run", "dist/talker_listener-0.1.0.juizapp"], 'listener_python receives "Hello, World!"')
        if ok and not stop_server(servers.pop()):
            ok = False
        # 基礎とアプリをインストールして名前で起動する
        for package in ["chatter_base", "chatter_listener"]:
            if not ok:
                break
            args = ["install", f"dist/{package}-0.1.0.juizapp"]
            returncode, stdout, stderr = run_call(juiz, args)
            print(f"juiz {' '.join(args)}\n  {stdout.strip()}", flush=True)
            if returncode != 0 or f"Installed {package} 0.1.0" not in stdout:
                print(f"NG: {package} をインストールできませんでした\n{stderr}", file=sys.stderr)
                ok = False
        ok = ok and start(["run", "chatter_base"], 'talker_python says "Hello from chatter_base"')
        ok = ok and start(["run", "chatter_listener"], 'listener_python receives "Hello from chatter_base"')
    except Exception as e:
        print(f"NG: {e}", file=sys.stderr)
        ok = False
    finally:
        # アプリを先に止める
        for server in reversed(servers):
            if server.poll() is None and not stop_server(server):
                ok = False
        for path in logs:
            if not ok:
                with open(path, encoding="utf-8", errors="replace") as f:
                    print(f"juiz の出力:\n{f.read()}", file=sys.stderr)
            os.unlink(path)
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(data_dir, ignore_errors=True)
    return ok


def main() -> int:
    juiz = shutil.which("juiz")
    if juiz is None:
        print("juiz コマンドが見つかりません (pip install -r requirements.txt を実行してください)", file=sys.stderr)
        return 1
    if not generate_python_types(juiz):
        return 1
    failed = [conf for conf, calls, expected in CASES if not run_case(juiz, conf, calls, expected)]
    if not run_two_namespaces(juiz):
        failed.append("increment_process.conf --namespace")
    if not run_mismatch(juiz):
        failed.append(MISMATCH_CONF)
    if not run_packages(juiz):
        failed.append("packages/")
    if failed:
        print(f"失敗したサンプル: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
