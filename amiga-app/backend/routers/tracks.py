from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Response
import json
from pathlib import Path

from backend.config import *
from pydantic import BaseModel
import signal
import os

router = APIRouter()


@router.get("/kill")
async def kill_app():
    os.kill(os.getpid(), signal.SIGTERM)
    return Response(status_code=200, content="Server shutting down...")


@router.get("/list_tracks")
async def list_tracks():
    """Lists all JSON track files in the `TRACKS_DIR` directory."""
    if not os.path.exists(TRACKS_DIR):
        os.mkdir(TRACKS_DIR)

    track_names = [f[:-5] for f in os.listdir(TRACKS_DIR) if f.endswith(".json")]

    return {"tracks": track_names}


@router.post("/delete_track/{track_name}")
async def delete_track(track_name):
    """Deletes a JSON track file from the  `TRACKS_DIR` directory."""
    json_path = Path(TRACKS_DIR) / (track_name + ".json")
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
@router.post("/edit_track")
async def edit_track_name(body: Edit):
    current_name = body.current_name
    new_name = body.new_name

    track_path = os.path.join(TRACKS_DIR, f"{current_name}.json")
    new_track_path = os.path.join(TRACKS_DIR, f"{new_name}.json")

    # Check if the current track file exists
    if not os.path.exists(track_path):
        return {"error": f"Track: '{current_name}' does not exist"}

    # Check if the new track name already exists
    if os.path.exists(new_track_path):
        return {"error": f"Track: '{new_name}' already exists"}

    os.rename(track_path, new_track_path)
    return {"message": f"Track: '{current_name}' renamed to: '{new_name}'."}


@router.get("/get_track/{track_name}")
async def get_track(track_name: str):
    """Reads a track JSON file and returns its content."""
    track_path = os.path.join(TRACKS_DIR, f"{track_name}.json")

    if not os.path.exists(track_path):
        return {"error": f"Track '{track_name}' not found."}

    with open(track_path, "r") as json_file:
        track_data = json.load(json_file)

    waypoints = track_data.get("waypoints", [])

    return {"track_name": track_name, "waypoints": waypoints}
