"""image_pipeline.conf の Composite 版と接続版を何度か呼び、1 回あたりの時間を出す。

`juiz -f image_pipeline.conf -d` を起動したまま、別のターミナルでリポジトリのルートから実行する:

    python scripts/time_image_pipeline.py [回数]

同じ処理を juiz を通さずに Python だけで実行した時間も並べて出す。
juiz の時間との差の多くは、段の間で画像を Python と juiz (Rust) の間で受け渡す (変換する) 時間である。
"""

import contextlib
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "http://127.0.0.1:8000"
ARGS = {"path": "images/sample.png", "width": 320, "height": 240, "threshold": 128}
# Composite は引数を渡して call、接続版は末端の ratio0 を execute (上流から値を集める)
TARGETS = [
    ("Composite (pipeline0)", "call", f"{BASE}/process/pipeline0::image_pipeline_python", ARGS),
    ("接続 (ratio0 を execute)", "execute", f"{BASE}/process/ratio0::image_white_ratio_python", {}),
]


def request(api: str, identifier: str, args: dict):
    url = f"{BASE}/api/process/{api}?" + urllib.parse.urlencode({"identifier": identifier})
    req = urllib.request.Request(url, data=json.dumps(args).encode(), method="PATCH",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def python_only():
    """juiz を通さず、同じ 4 つの関数を Python で直接つないで呼ぶ。"""
    sys.path.insert(0, os.path.join(ROOT, "process"))
    with contextlib.redirect_stdout(io.StringIO()):  # pyjuiz が読み込み時に出す表示を隠す
        from image_load_python import image_load_python
        from image_resize_python import image_resize_python
        from image_binarize_python import image_binarize_python
        from image_white_ratio_python import image_white_ratio_python
    path = os.path.join(ROOT, ARGS["path"])
    return lambda: image_white_ratio_python(image_binarize_python(
        image_resize_python(image_load_python(path), ARGS["width"], ARGS["height"]), ARGS["threshold"]))


def measure(f, n: int):
    f()  # 1 回目は読み込みなどが入るので数えない
    start = time.perf_counter()
    for _ in range(n):
        result = f()
    return (time.perf_counter() - start) / n * 1000, result


def main() -> int:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    print(f"{n} 回の平均")
    for label, api, identifier, args in TARGETS:
        ms, result = measure(lambda: request(api, identifier, args), n)
        print(f"  {ms:8.2f} ms  {label}  (結果 {result})")
    ms, result = measure(python_only(), n)
    print(f"  {ms:8.2f} ms  Python だけ (juiz を通さない)  (結果 {result})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
