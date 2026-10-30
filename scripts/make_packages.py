"""packages/ の下のアプリを .juizapp にする。

    python scripts/make_packages.py [-o dist]

packages/<名前>/ には juizapp.yaml と conf だけを置き、Process の .py は process/ のものを写して使う
(同じファイルを 2 か所に置かないため)。写した結果を build/packages/<名前>/ に作り、
`juiz pack` で <出力先>/<名前>-<版>.juizapp を作る。Python だけのパッケージなので、
どの OS で作っても同じものになる (targets: [any])。
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# パッケージ名 → python/ に写す process/ の .py
PACKAGES = {
    "talker_listener": ["talker_python.py", "listener_python.py"],
    "chatter_base": ["talker_python.py"],
    "chatter_listener": ["listener_python.py"],
}


def stage(name: str, sources: list[str]) -> str:
    """build/packages/<name>/ に packages/<name>/ と Process の .py を写し、そのパスを返す。"""
    dest = os.path.join(ROOT, "build", "packages", name)
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "packages", name), dest)
    os.makedirs(os.path.join(dest, "python"))
    for source in sources:
        shutil.copy2(os.path.join(ROOT, "process", source), os.path.join(dest, "python", source))
    for license_file in ["LICENSE-MIT", "LICENSE-APACHE"]:
        shutil.copy2(os.path.join(ROOT, license_file), os.path.join(dest, license_file))
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-o", "--out", default="dist", help="出力先のディレクトリ (既定は dist)")
    parser.add_argument("names", nargs="*", help="作るパッケージの名前 (省けば全部)")
    args = parser.parse_args()
    juiz = shutil.which("juiz")
    if juiz is None:
        print("juiz コマンドが見つかりません (pip install -r requirements.txt を実行してください)", file=sys.stderr)
        return 1
    out = os.path.join(ROOT, args.out)
    os.makedirs(out, exist_ok=True)
    for name in args.names or PACKAGES:
        if name not in PACKAGES:
            print(f"知らないパッケージです: {name} ({', '.join(PACKAGES)})", file=sys.stderr)
            return 1
        result = subprocess.run([juiz, "pack", stage(name, PACKAGES[name]), "-o", out], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
