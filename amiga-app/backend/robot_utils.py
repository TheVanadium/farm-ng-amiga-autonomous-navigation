from farm_ng.track.track_pb2 import Track
from farm_ng_core_pybind import Isometry3F64
from farm_ng_core_pybind import Pose3F64
from farm_ng_core_pybind import Rotation3F64

import numpy as np


def format_track(track_waypoints: list[Pose3F64]) -> Track:
    """Pack the track waypoints into a Track proto message.

    Args:
        track_waypoints (list[Pose3F64]): The track waypoints.
    """
    return Track(waypoints=[pose.to_proto() for pose in track_waypoints])


def walk_towards(
    current_pose: Pose3F64, target_position: np.ndarray, goal_counter: int
) -> tuple[list[Pose3F64], int]:
    """_summary_
    Given the robot's current pose, outputs the list of poses the robot must use in their track to walk towards the target position
    Also outputs the index of the waypoint where the robot begins walking forward
    Args:
        current_pose (Pose3F64): Current position / rotation of robot
        position (np.array): Target position

    Returns:
        tuple[list[Pose3F64], int]
    """
    current_position = np.array(current_pose.translation[:2])
    rotation_matrix = current_pose.rotation.rotation_matrix
    cos_theta = rotation_matrix[0][0]
    sin_theta = rotation_matrix[1][0]
    current_angle = np.acos(cos_theta)
    if sin_theta < 0:
        current_angle = -current_angle
    diff = target_position - current_position
    distance = np.linalg.norm(diff)
    target_angle = np.acos(diff[0] / distance)
    if diff[1] < 0:
        target_angle = -target_angle

    angle_diff = target_angle - current_angle

    turn = create_turn_segment(current_pose, angle_diff, f"goal{goal_counter}")
    print(f"Goal {goal_counter}: Walking from {current_position} to {target_position}")
    print(
        f"Facing {current_angle}, target: {target_angle}. Rotating {angle_diff} radians"
    )
    if turn != []:
        current_pose = turn[-1]
    cutoff = len(turn)
    turn.extend(
        create_straight_segment(
            current_pose, float(distance), f"goal{goal_counter + 1}"
        )
    )
    print(f"Walking forward {distance} meters")
    return turn, cutoff


def create_straight_segment(
    previous_pose: Pose3F64, distance: float, next_frame_b: str, spacing: float = 0.1
) -> list[Pose3F64]:
    """Compute a straight line segment

    Args:
        previous_pose (Pose3F64): The previous pose.
        distance (float): The length of the line, in meters.
        spacing (float): The spacing between waypoints, in meters.

    Returns:
        Pose3F64: The poses of the straight segment.
    """
    # Create a container to store the track segment waypoints
    segment_poses: list[Pose3F64] = [previous_pose]

    # For tracking the number of segments and remaining angle
    first_segment = True
    remaining_distance: float = distance
    counter = 0

    while remaining_distance > 0:
        # Compute the distance of the next segment
        segment_distance: float = min(remaining_distance, spacing)

        # Compute the next pose
        straight_segment: Pose3F64 = Pose3F64(
            a_from_b=Isometry3F64([segment_distance, 0, 0], Rotation3F64.Rz(0)),
            frame_a=segment_poses[-1].frame_b,
            frame_b=f"{next_frame_b}.{counter}",
        )
        if first_segment:
            segment_poses = [previous_pose * straight_segment]
            first_segment = False
        else:
            segment_poses.append(segment_poses[-1] * straight_segment)

        counter += 1

        # Update the remaining angle
        remaining_distance -= segment_distance

    segment_poses[-1].frame_b = next_frame_b
    return segment_poses


def create_turn_segment(
    previous_pose: Pose3F64, angle: float, next_frame_b: str, spacing: float = 0.1
) -> list[Pose3F64]:
    """Compute a turn segment of a square.

    Args:
        previous_pose (Pose3F64): The previous pose.
        next_frame_b (str): The name of the child frame of the next pose.
        angle (float): The angle to turn, in radians (+ left, - right).
        spacing (float): The spacing between waypoints, in radians.
    Returns:
        list[Pose3F64]: The poses of the turn segment.
    """
    # Normalize the angle within 0->2pi
    angle = angle % (2 * np.pi)
    # Don't rotate 270deg when we can rotate -90deg
    if angle > np.pi:
        angle = -2 * np.pi + angle
    # Create a container to store the track segment waypoints
    segment_poses: list[Pose3F64] = [previous_pose]

    # For tracking the number of segments and remaining angle
    first_segment = True
    remaining_angle: float = angle
    counter = 0

    while abs(remaining_angle) > 0:
        # Compute the angle of the next segment
        segment_magnitude = min(np.abs(remaining_angle), spacing)
        segment_angle: float = np.copysign(segment_magnitude, angle)

        # Compute the next pose
        turn_segment: Pose3F64 = Pose3F64(
            a_from_b=Isometry3F64.Rz(segment_angle),
            frame_a=segment_poses[-1].frame_b,
            frame_b=f"{next_frame_b}.{counter}",
        )
        if first_segment:
            segment_poses = [previous_pose * turn_segment]
            first_segment = False
        else:
            segment_poses.append(segment_poses[-1] * turn_segment)

        # Update the counter and remaining angle
        counter += 1
        remaining_angle -= segment_angle

    segment_poses[-1].frame_b = next_frame_b
    return segment_poses
