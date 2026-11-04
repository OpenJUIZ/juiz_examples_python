"""Transformations のサンプル: 台車 → 雲台 → カメラ の部品 (OpenJUIZ/juiz#374)。

位置姿勢 (ContainerPose) は juiz が Container ごとに持ち、利用者の状態とは別にある。
部品のつながり (Transform) と基点 (Anchor) は transformations.conf に書く:

    map (Periodic) → odom (Static) → base0 (mobile_base_python) → pantilt0 (pantilt_python) → camera0 (camera_python)

- mobile_base_python_move はオドメトリを積分して、odom から見た自分の位置姿勢を set_pose で書く。
- pantilt_python_set_pan はパン角を書く (台車から見た自分の向きだけを変える)。
- camera_python_pose は基準から見た自分の位置姿勢を pose で読む。カメラは Transform で雲台につながっているだけ。
  読むだけなので readonly=True にしている。
- pose_print_python は Pose 通知 (conf の pose_listeners:) で呼ばれる Process。
"""

import math

from juiz import juiz_container, juiz_container_process, juiz_process, pose, set_pose
from juiz_std.geometry import Point3D, Pose, PoseStamped, Quaternion


def yaw_quaternion(yaw: float) -> Quaternion:
    """z 軸まわりに yaw [rad] 回す四元数 (x, y, z, w)"""
    return Quaternion(x=0.0, y=0.0, z=math.sin(yaw / 2), w=math.cos(yaw / 2))


def quaternion_yaw(q: Quaternion) -> float:
    """四元数の z 軸まわりの回転角 [rad] (ROS の RPY のヨー)"""
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


class MobileBase:
    """台車。オドメトリ (odom から見た x, y, 向き theta) を自分で積分して持つ"""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0


@juiz_container
def mobile_base_python() -> MobileBase:
    """台車"""
    return MobileBase()


@juiz_container_process(container_type="mobile_base_python")
def mobile_base_python_move(base, vx: float = 0.0, omega: float = 0.0, dt: float = 1.0,
                            reference: str = "odom") -> PoseStamped:
    """速度 vx [m/s]・角速度 omega [rad/s] で dt [s] 動かし、基準 reference (odom) から見た位置姿勢を書く"""
    base.x += vx * math.cos(base.theta) * dt
    base.y += vx * math.sin(base.theta) * dt
    base.theta += omega * dt
    p = Pose(position=Point3D(x=base.x, y=base.y, z=0.0), orientation=yaw_quaternion(base.theta))
    # odom → base0 の Transform が書き換わり、Pose 通知が出る
    return set_pose(base, reference, p)


class Pantilt:
    """雲台。パン角を持つ"""

    def __init__(self):
        self.pan = 0.0


@juiz_container
def pantilt_python() -> Pantilt:
    """雲台"""
    return Pantilt()


@juiz_container_process(container_type="pantilt_python")
def pantilt_python_set_pan(pantilt, pan: float = 0.0, reference: str = "base0") -> PoseStamped:
    """パン角 pan [rad] にする。取り付け位置はそのままで、基準 reference (台車) から見た向きだけを変える"""
    pantilt.pan = pan
    mount = pose(pantilt, reference).pose.position
    return set_pose(pantilt, reference, Pose(position=mount, orientation=yaw_quaternion(pan)))


class Camera:
    """カメラ。利用者の状態は持たない"""


@juiz_container
def camera_python() -> Camera:
    """カメラ"""
    return Camera()


# 読むだけなので readonly にする (OpenJUIZ/juiz#377)。juiz は Container を読み出しロックで呼ぶので、
# 同じ Container の readonly 同士は並行に走る。中で set_pose を呼ぶと PoseNotWritableError になる
@juiz_container_process(container_type="camera_python", readonly=True)
def camera_python_pose(camera, reference: str = "map") -> PoseStamped:
    """基準 reference から見た自分の位置姿勢"""
    return pose(camera, reference)


@juiz_process
def pose_print_python(pose: PoseStamped) -> str:
    """Pose 通知の受け手。受け取った位置姿勢を表示する"""
    p = pose.pose
    text = (f"pose_print_python: x={p.position.x:.2f} y={p.position.y:.2f} "
            f"yaw={math.degrees(quaternion_yaw(p.orientation)):.1f}deg (from {pose.header.frame_id})")
    print(text)
    return text
