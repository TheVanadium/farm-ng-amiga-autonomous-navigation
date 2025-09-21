import asyncio
import json
from multiprocessing import Queue
import os

from farm_ng.core.event_client_manager import EventClient
from farm_ng.track.track_pb2 import (
    Track,
    TrackFollowRequest,
    TrackFollowerState,
    TrackStatusEnum,
    TrackFollowerProgress,
)
from farm_ng.filter.filter_pb2 import FilterState
from farm_ng_core_pybind import Isometry3F64, Pose3F64
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.uri_pb2 import Uri

import numpy as np

from fastapi import BackgroundTasks, APIRouter, Request

from pydantic import BaseModel

from google.protobuf.empty_pb2 import Empty
import shutil


from pathlib import Path

from backend.config import LINES_DIR, POINTCLOUD_DATA_DIR, StateVars
from backend.robot_utils import walk_towards, format_track

from OakManager import OakManager

router = APIRouter()


async def get_pose(filter_client: EventClient) -> Pose3F64:
    """Get the current pose of the robot in the world frame, from the filter service.

    Args:
        filter_client: EventClient for the filter service
    """
    # We use the FilterState as the best source of the current pose of the robot
    state: FilterState = await filter_client.request_reply(
        "/get_state", Empty(), decode=True
    )
    return Pose3F64.from_proto(state.pose)


@router.get("/line/list")
async def list_lines(request: Request):
    if not os.path.exists(LINES_DIR):
        return {"error": "No tracks directory found."}

    line_names = [f[:-5] for f in os.listdir(LINES_DIR) if f.endswith(".json")]

    return {"lines": line_names}


@router.post("/line/record/start/{track_name}")
async def start_recording(request: Request, track_name: str):
    """Starts recording a track using the filter service client."""
    sv: StateVars = request.state.sv
    if sv.line_recording is not None:
        return {"error": "Line recording already in progress"}

    sv.line_recording = track_name

    client = request.state.event_manager.clients["filter"]
    sv.line_start = np.array((await get_pose(client)).translation[:2])

    return {"message": f"Recording started for track '{track_name}'."}


@router.post("/line/end_creation")
async def end_creation(request: Request):
    sv: StateVars = request.state.sv
    sv.line_recording = None
    sv.turn_calibrating = False


###stop###
@router.post("/line/record/stop")
async def stop_recording(request: Request):
    """Stops the recording process."""

    sv: StateVars = request.state.sv
    if not sv.line_recording:
        return {"error": "No recording in progress."}

    client = request.state.event_manager.clients["filter"]
    sv.line_end = np.array((await get_pose(client)).translation[:2])
    return {"message": "Recording stopped successfully."}


@router.post("/line/calibrate_turn/start")
async def calibrate_turn(request: Request):
    sv: StateVars = request.state.sv
    if sv.turn_calibrating:
        return {"error": "Turn calibration is already active"}
    filter_client = request.state.event_manager.clients["filter"]
    sv.turn_calibration_start = await get_pose(filter_client)
    sv.turn_calibration_segments = 1
    sv.turn_calibrating = True
    return {"message": "Turn calibration started."}


@router.post("/line/calibrate_turn/segment")
async def add_turn_segment(request: Request):
    sv: StateVars = request.state.sv
    if not sv.turn_calibrating:
        return {"error": "Turn calibration is not active."}
    sv.turn_calibration_segments += 1


@router.post("/line/calibrate_turn/end")
async def end_turn_calibration(request: Request):
    sv: StateVars = request.state.sv
    if not sv.turn_calibrating:
        return {"error": "Turn calibration is not active"}
    filter_client = request.state.event_manager.clients["filter"]
    sv.turn_calibrating = False
    num_segments = sv.turn_calibration_segments
    start_position = np.array(sv.turn_calibration_start.translation[:2])
    end_position = np.array((await get_pose(filter_client)).translation[:2])
    turn_diff = end_position - start_position
    line_diff = sv.line_end - sv.line_start
    line_direction = line_diff / np.linalg.norm(line_diff)
    left_turn_direction = np.array((-line_direction[1], line_direction[0]))
    turn_length = np.abs((turn_diff / num_segments).dot(left_turn_direction))
    sv.turn_length = turn_length

    line_data = {
        "start": sv.line_start.tolist(),
        "end": sv.line_end.tolist(),
        "turn_length": turn_length,
    }
    json_text = json.dumps(line_data)
    output_dir = Path(LINES_DIR)
    json_path = output_dir / f"{sv.line_recording}.json"
    with open(json_path, "w") as line_file:
        line_file.write(json_text)

    sv.line_recording = None

    return {"message": "Turn calibration complete."}


def clear_line_data(line_name: str):
    line_path = f"{POINTCLOUD_DATA_DIR}/{line_name}"
    if not os.path.exists(line_path):
        return
    shutil.rmtree(line_path)


class LineFollowData(BaseModel):
    num_rows: int
    first_turn_right: bool


@router.post("/line/follow/{line_name}")
async def follow_line(
    request: Request,
    line_name: str,
    data: LineFollowData,
    background_tasks: BackgroundTasks,
):
    sv: StateVars = request.state.sv
    if sv.following_track:
        return {"error": "Line is currently being followed"}

    line_path = Path(LINES_DIR) / f"{line_name}.json"

    if not line_path.exists():
        return {"error": f"Track: '{line_name} does not exist"}

    with open(line_path, "r") as line_file:
        line_data = json.loads(line_file.read())
    line_start = np.array(line_data["start"])
    line_end = np.array(line_data["end"])
    turn_length = line_data["turn_length"]

    if sv.following_track:
        return {"error": "Line is currently being followed"}

    remaining_rows = data.num_rows
    event_manager = request.state.event_manager
    filter_client = event_manager.clients["filter"]

    current_pose = await get_pose(filter_client)
    current_pose = current_pose * Pose3F64(
        a_from_b=Isometry3F64(), frame_a="robot", frame_b="goal0"
    )
    goal_counter = 1
    total_path: list[Pose3F64] = [current_pose]
    current_path, _ = walk_towards(current_pose, line_start, goal_counter)
    total_path.extend(current_path)
    row_indices: list[tuple[int, int]] = []
    goal_counter += 2

    def _current_pose():
        return total_path[-1]

    walking_forward = True

    line_delta = line_end - line_start
    while remaining_rows > 0:
        current_position = np.array(_current_pose().translation[:2])
        delta = line_delta if walking_forward else -line_delta
        target_position = current_position + delta
        current_path, rotate_cutoff = walk_towards(
            _current_pose(), target_position, goal_counter
        )
        # rotate_index = Index of the 1st waypoint where the robot begins walking along the row
        rotate_index = len(total_path) + rotate_cutoff
        total_path.extend(current_path)
        # len(total_path) = Index of the first waypoint where robot isn't walking along the row
        row_indices.append((rotate_index, len(total_path)))
        goal_counter += 2
        # If this was the last row, we should not prepare for the next turn
        if remaining_rows == 1:
            break
        current_position = np.array(_current_pose().translation[:2])
        # This vector faces a 90 degree clockwise rotation of line_delta
        forward_right_direction = np.array([line_delta[1], -line_delta[0]])
        forward_right_direction = forward_right_direction / np.linalg.norm(
            forward_right_direction
        )
        # The vector direction of each turn is always the same, because the robot is always moving towards either the right or left side of the field
        turn_direction = (
            forward_right_direction
            if data.first_turn_right
            else -forward_right_direction
        )
        turn_vector = turn_direction * turn_length
        target_position = current_position + turn_vector
        current_path, rotate_cutoff = walk_towards(
            _current_pose(), target_position, goal_counter
        )
        rotate_index = len(total_path) + rotate_cutoff
        total_path.extend(current_path)
        goal_counter += 2

        walking_forward = not walking_forward
        remaining_rows -= 1

    track_client = event_manager.clients["track_follower"]
    line_track: Track = format_track(total_path)

    clear_line_data(line_name)
    await track_client.request_reply("/set_track", TrackFollowRequest(track=line_track))
    await track_client.request_reply("/start", Empty())
    sv.following_track = True

    background_tasks.add_task(
        handle_image_capture,
        sv,
        request.state.oak_manager,
        track_client,
        line_name,
        row_indices,
    )

    return {"message": "Line follow started"}


async def handle_image_capture(
    sv: StateVars,
    oak_manager: OakManager,
    client: EventClient,
    line_name: str,
    row_indices: list[tuple[int, int]],
):
    """_summary_

    Args:
        client (EventClient): Track Follower Client
        sv (StateVars):
        row_indices (list[tuple[int, int]]):
    """
    current_row_number = -1
    last_image_capture = 0
    # The robot must move a tiny distance at the start of each row
    # To straighten itself
    initial_distance_offset: float = 0.5
    # should correspond to the size of the bounding box defined in volume estimation
    bounding_box_length: float = 0.5

    sv.track_follow_id += 1
    track_follow_id = sv.track_follow_id
    capture_number = 0

    async for _, message in client.subscribe(
        SubscribeRequest(
            uri=Uri(path="/state", query="service_name=track_follower"),
            every_n=1,
        ),
        decode=True,
    ):
        if track_follow_id != sv.track_follow_id:
            print("Exiting old loop")
            break
        state: TrackFollowerState = message
        track_status = state.status.track_status

        if track_status == TrackStatusEnum.TRACK_PAUSED:
            pass
        else:
            progress: TrackFollowerProgress = state.progress
            goal_index = progress.goal_waypoint_index
            calculated_row_number = 0
            for ind1, ind2 in row_indices:
                # We go from [ind1 -> ind2) on each row
                if goal_index >= ind1 and goal_index < ind2:
                    break
                calculated_row_number += 1
            walking_row = calculated_row_number != len(row_indices)
            if not walking_row:
                continue
            dist_remaining = progress.distance_remaining
            if current_row_number != calculated_row_number:
                # We have started a new segment
                current_row_number = calculated_row_number
                print(f"Started row segment: {current_row_number}")
                last_image_capture = dist_remaining - initial_distance_offset
                capture_number = 0
            else:
                distance_travelled = last_image_capture - dist_remaining
                if distance_travelled > bounding_box_length:
                    print(
                        f"Travelled a distance of {distance_travelled} meters. Capturing image"
                    )
                    last_image_capture = dist_remaining
                    await client.request_reply("/pause", Empty())
                    await capture_image(
                        oak_manager,
                        line_name,
                        current_row_number,
                        capture_number,
                    )
                    print("Image saved")
                    capture_number += 1
                    await client.request_reply("/resume", Empty())


async def capture_image(
    oak_manager: OakManager, line_name: str, row_number: int, capture_number: int
):
    msg = {
        "action": "save_point_cloud",
        "line_name": line_name,
        "row_number": row_number,
        "capture_number": capture_number,
    }

    oak_manager.queue_msg(msg)

    # Pause the robot in place to mitigate motion blur or account for camera latency
    capture_pause_time: float = 1.2
    await asyncio.sleep(capture_pause_time)


@router.post("/line/delete/{track_name}")
async def delete_track(track_name):
    """Deletes a JSON track file from the  `TRACKS_DIR` directory."""
    json_path = Path(LINES_DIR) / (track_name + ".json")
    try:
        json_path.unlink()
    except FileNotFoundError:
        return {"error": f"Track: '{track_name}' does not exist"}

    return {"message": f"Track: '{track_name}' deleted"}


# Define Pydantic model for request data
class Edit(BaseModel):
    current_name: str
    new_name: str


# Only one definition of the endpoint
@router.post("/line/edit")
async def edit_line_name(body: Edit):
    current_name = body.current_name
    new_name = body.new_name

    line_path = os.path.join(LINES_DIR, f"{current_name}.json")
    new_line_path = os.path.join(LINES_DIR, f"{new_name}.json")

    # Check if the current track file exists
    if not os.path.exists(line_path):
        return {"error": f"Track: '{current_name}' does not exist"}

    # Check if the new track name already exists
    if os.path.exists(new_line_path):
        return {"error": f"Track: '{new_name}' already exists"}

    os.rename(line_path, new_line_path)
    return {"message": f"Track: '{current_name}' renamed to: '{new_name}'."}


@router.get("/line/get_start/{line_name}")
async def get_start(line_name: str):
    """Reads a track JSON file and returns its content."""
    line_path = os.path.join(LINES_DIR, f"{line_name}.json")

    if not os.path.exists(line_path):
        return {"error": f"Line '{line_name}' not found."}

    with open(line_path, "r") as json_file:
        line_data = json.loads(json_file.read())
    return {"start_position": line_data["start"]}
