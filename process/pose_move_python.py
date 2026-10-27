# 型付きの引数と戻り値を持つ Python の Process。
# 型は types/geometry.jidl から `juiz idl -g python -o gen types/geometry.jidl` で作ったもの (gen/)
import math

from juiz import juiz_process
from examples.geometry import Point2D, Pose2D, Twist2D


@juiz_process
def pose_move_python(pose: Pose2D = Pose2D(), twist: Twist2D = Twist2D(), dt: float = 1.0) -> Pose2D:
    """姿勢 pose から速度 twist で dt 秒動いた姿勢を返す"""
    distance = twist.linear * dt
    moved = Pose2D(position=Point2D(x=pose.position.x + distance * math.cos(pose.theta),
                                    y=pose.position.y + distance * math.sin(pose.theta)),
                   theta=pose.theta + twist.angular * dt,
                   frame_id=pose.frame_id)
    print(f"pose_move_python: ({pose.position.x:.2f}, {pose.position.y:.2f}, {pose.theta:.2f}) -> "
          f"({moved.position.x:.2f}, {moved.position.y:.2f}, {moved.theta:.2f})")
    return moved
