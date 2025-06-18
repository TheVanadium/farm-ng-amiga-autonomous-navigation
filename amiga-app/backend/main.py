# Copyright (c) farm-ng, inc.
#
# Licensed under the Amiga Development Kit License (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/farm-ng/amiga-dev-kit/blob/main/LICENSE
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import signal
import sys
import os
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Navigate one directory out of the location of main.py
os.chdir(f"{Path(__file__).parent}/..")

import asyncio
from farm_ng.core.event_client_manager import EventClient
from fastapi import WebSocket, WebSocketDisconnect
from farm_ng.core.event_service_pb2 import SubscribeRequest
from farm_ng.core.uri_pb2 import Uri
from google.protobuf.json_format import MessageToJson  # type: ignore


import uvicorn
from farm_ng.core.event_client_manager import EventClientSubscriptionManager
from farm_ng.core.event_service_pb2 import EventServiceConfigList
from farm_ng.core.events_file_reader import proto_from_json_file


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from multiprocessing import Process, Queue

# this is bad, but I can't figure out how to import config mypy complaining
import config  # type: ignore

from routers import tracks, record, follow, linefollow, pointcloud

from cameraBackend.oakManager import startCameras

from typing import AsyncGenerator, Any, Optional
from typing import Optional

global oak_manager
oak_manager: Optional[Process] = None
global camera_msg_queue
camera_msg_queue: Queue = Queue()

DEV_MODE: bool = True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    print("Initializing App...")

    if DEV_MODE:
        yield {
            "event_manager": None,
            "oak_manager": None,
            "camera_msg_queue": None,
            "vars": None,
        }
        oak_manager = None

    else:
        # config with all the configs
        base_config_list: EventServiceConfigList = proto_from_json_file(
            args.config, EventServiceConfigList()
        )

        # filter out services to pass to the events client manager
        service_config_list = EventServiceConfigList()
        for config in base_config_list.configs:
            if config.port == 0:
                continue
            service_config_list.configs.append(config)

        event_manager = EventClientSubscriptionManager(config_list=service_config_list)

        no_cameras = False
        if no_cameras:
            oak_manager = None
        else:
            oak_manager = Process(
                target=startCameras, args=(camera_msg_queue, config.POINTCLOUD_DATA_DIR)
            )
            oak_manager.start()
            print(f"Starting oak manager with PID {oak_manager.pid}")

        asyncio.create_task(event_manager.update_subscriptions())

        yield {
            "event_manager": event_manager,
            "oak_manager": oak_manager,
            "camera_msg_queue": camera_msg_queue,
            # Yield dict cannot be changed directly, but objects inside it can
            # So we use a vars item for all our non constant variables
            "vars": config.StateVars(),
        }

    # Shutdown cameras properly
    if oak_manager != None:
        print("Stopping camera services...")
        oak_manager.terminate()
        oak_manager.join()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(tracks.router)
app.include_router(record.router)
app.include_router(follow.router)
app.include_router(linefollow.router)
app.include_router(pointcloud.router)


# not sure why params are necessary but won't touch it in case the robot complains
# could use testing
def handle_sigterm(signum: Any, frame: Any) -> None:
    print("Received SIGTERM, stopping camera services")

    if oak_manager != None:
        oak_manager.terminate()
        oak_manager.join()
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_sigterm)


@app.websocket("/filter_data")
async def filter_data(websocket: WebSocket, every_n: int = 3) -> None:
    """Coroutine to subscribe to filter state service via websocket.

    Args:
        websocket (WebSocket): the websocket connection
        every_n (int, optional): the frequency to receive events.

    Usage:
        ws = new WebSocket(`${API_URL}/filter_data`)
    """
    event_manager = websocket.state.event_manager
    full_service_name = "filter"
    client: EventClient = event_manager.clients[full_service_name]

    await websocket.accept()

    disconnected = False

    async for _, msg in client.subscribe(
        SubscribeRequest(
            uri=Uri(path=f"/state", query=f"service_name={full_service_name}"),
            every_n=every_n,
        ),
        decode=True,
    ):
        try:
            await websocket.send_json(MessageToJson(msg))
        except WebSocketDisconnect as e:
            disconnected = True
            break

    if not disconnected:
        await websocket.close()


if __name__ == "__main__":
    # get command line arg --debug
    import argparse

    parser = argparse.ArgumentParser(description="Run the FastAPI server.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run the server in debug mode, serving the React app.",
    )

    # Ensure PORT is defined, either from config or set a default value
    try:
        PORT = config.PORT
    except AttributeError:
        raise AttributeError(
            "PORT is not defined in the config module. Please set it before running the server."
        )

    class Arguments:
        def __init__(self, config: str, port: int, debug: bool = False) -> None:
            self.config = config
            self.port = port
            self.debug = debug

    args = Arguments(
        config="/opt/farmng/config.json", port=PORT, debug=parser.parse_args().debug
    )

    # NOTE: we only serve the react app in debug mode

    if args.debug:
        react_build_directory = Path(__file__).parent / ".." / "ts" / "dist"
        print(f"Serving React app from {react_build_directory.resolve()}")
        app.mount(
            "/",
            StaticFiles(directory=str(react_build_directory.resolve()), html=True),
        )

    # print(f"camera PID: {oakManager.pid}")

    # run the server
    uvicorn.run(app, host="0.0.0.0", port=args.port)  # noqa: S104
