"""types/geometry.jidl の process 宣言から作った client stub (PoseMoveClient) で、move0 を呼ぶ。

`juiz idl -g python -o gen types/geometry.jidl` で型を作り、`juiz -f typed_pose.conf -d` を起動したまま、
別のターミナルでリポジトリのルートから実行する:

    python scripts/pose_client.py

引数を生成した型 (Pose2D・Twist2D) で渡し、戻り値も Pose2D で受け取る。
move0 は Python の Process だが、ほかの言語のサンプル (juiz_examples_rust など) の pose_move でも同じように呼べる。
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(ROOT, "gen"))

from examples.geometry import Point2D, Pose2D, PoseMoveClient, Twist2D  # noqa: E402


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "move0"
    move = PoseMoveClient.connect(name)
    pose = Pose2D(position=Point2D(x=1.0, y=2.0))
    moved = move(pose, Twist2D(linear=1.0), dt=2.0)
    print(f"{type(moved).__name__}: x={moved.position.x:.2f} y={moved.position.y:.2f} "
          f"theta={moved.theta:.2f} frame_id={moved.frame_id}")
    # 既定値のある引数 (dt = 1.0) は省ける
    print(f"dt omitted: x={move(pose, Twist2D(linear=1.0)).position.x:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
