from pathlib import Path

from farm_ng.core.events_file_reader import proto_from_json_file
from farm_ng.track.track_pb2 import Track, TrackFollowRequest, TrackFollowerState

from fastapi import APIRouter, Request
from google.protobuf.empty_pb2 import Empty

from grpc.aio import AioRpcError

from backend.config import *


router = APIRouter()


@router.post("/follow/start/{track_name}")
async def follow_track(request: Request, track_name: str):
    """Instructs the robot to follow an existing recorded track."""
    event_manager = request.state.event_manager

    track_path = Path(TRACKS_DIR) / f"{track_name}.json"
    client = event_manager.clients["track_follower"]

    if not track_path.exists():
        return {"error": f"Track: '{track_name} does not exist"}

    track: Track = proto_from_json_file(track_path, Track())

    await client.request_reply("/set_track", TrackFollowRequest(track=track))
    await client.request_reply("/start", Empty())

    return {"message": f"Following track '{track_name}'."}


@router.get("/follow/state")
async def follower_state(request: Request):
    event_manager = request.state.event_manager
    client = event_manager.clients["track_follower"]

    state: TrackFollowerState = await client.request_reply(
        "/get_state", Empty(), decode=True
    )

    failures = state.status.robot_status.failure_modes
    return {"controllable": failures == []}


@router.post("/follow/pause")
async def pause_following(request: Request):
    """Instructs the robot to pause track following."""
    event_manager = request.state.event_manager
    client = event_manager.clients["track_follower"]
    try:
        await client.request_reply("/pause", Empty())
    except AioRpcError:
        # return {"error": "Not currently following a track"}
        pass

    return {"message": "Pausing track following"}


# Resume
@router.post("/follow/resume")
async def resume_following(request: Request):
    """Instructs the robot to resume track following."""
    event_manager = request.state.event_manager
    client = event_manager.clients["track_follower"]

    try:
        await client.request_reply("/resume", Empty())
    except AioRpcError:
        # return {"error": "Not currently following a track"}
        pass

    return {"message": "Resuming track following"}


@router.post("/follow/stop")
async def stop_following(request: Request):
    """Instructs the robot to stop track following."""
    event_manager = request.state.event_manager
    vars: StateVars = request.state.vars
    client = event_manager.clients["track_follower"]
    try:
        await client.request_reply("/cancel", Empty()), 0.5
    except AioRpcError:
        return {"success": False, "message": "Failed to call /cancel"}

    vars.following_track = False

    return {"success": True, "message": "Stopping track following"}
