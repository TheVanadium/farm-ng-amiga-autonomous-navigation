import asyncio
import json

from farm_ng.core.event_client_manager import EventClient
from farm_ng.core.events_file_writer import proto_to_json_file
from farm_ng.core.event_service_pb2 import EventServiceConfig
from farm_ng.track.track_pb2 import Track
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.uri_pb2 import Uri

from fastapi import HTTPException
from fastapi import BackgroundTasks
from fastapi import APIRouter

from google.protobuf.json_format import ParseDict
from google.protobuf.empty_pb2 import Empty
from fastapi import Request

from pathlib import Path

from backend.config import *

router = APIRouter()


@router.post("/record/start/{track_name}")
async def start_recording(
    request: Request, track_name: str, background_tasks: BackgroundTasks
):
    """Starts recording a track using the filter service client."""
    vars: StateVars = request.state.vars
    recording_active = vars.track_recording
    if recording_active:
        return {"error": "recording is already active"}

    vars.track_recording = True  # Set recording flag to true
    output_dir = Path(TRACKS_DIR)

    # Run the recording as a background task
    background_tasks.add_task(record_track, request, track_name, output_dir)

    return {"message": f"Recording started for track '{track_name}'."}


async def record_track(request: Request, track_name: str, output_dir: Path) -> None:
    """Runs the filter service client to record a track."""
    vars: StateVars = request.state.vars
    vars.track_recording = True

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    event_manager = request.state.event_manager
    service_name = "filter"
    client: EventClient = event_manager.clients[service_name]

    # Create a Track message
    track = Track()

    # Subscribe to the filter track topic
    async for _, message in client.subscribe(
        SubscribeRequest(
            uri=Uri(path=f"/track", query=f"service_name={service_name}"),
            every_n=1,
        ),
        decode=True,
    ):
        if not vars.track_recording:
            print("Track Recording stopped.")
            break

        # print("Adding to track:", message)
        next_waypoint = track.waypoints.add()
        next_waypoint.CopyFrom(message)

    track_file = output_dir / f"{track_name}.json"
    proto_to_json_file(track_file, track)


###stop###
@router.post("/record/stop")
async def stop_recording(request: Request):
    """Stops the recording process."""
    vars: StateVars = request.state.vars
    recording_active = vars.track_recording
    if not recording_active:
        return {"message": "No recording in progress."}

    vars.track_recording = False  # Stop the recording process
    return {"message": "Recording stopped successfully."}
