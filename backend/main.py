from __future__ import annotations
import signal, sys, os, asyncio, argparse
from pathlib import Path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.chdir(f"{Path(__file__).parent}/..")
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from farm_ng.core.event_client_manager import EventClient, EventClientSubscriptionManager
from farm_ng.core.event_service_pb2 import SubscribeRequest, EventServiceConfigList
from farm_ng.core.uri_pb2 import Uri
from farm_ng.core.events_file_reader import proto_from_json_file
from google.protobuf.json_format import MessageToJson  # type: ignore
import uvicorn, config
from routers import tracks, record, follow, linefollow
from OakManager import OakManager
from typing import AsyncGenerator, Any, Optional

global oak_manager
oak_manager: Optional[OakManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[dict, None]:
    services = await setup_services(args=cli_args)
    yield services

    if services["oak_manager"] is not None: services["oak_manager"].shutdown()

async def setup_services(args: argparse.Namespace) -> dict[str, Any]:
    # config with all the configs, then filter out services to pass to the events client manager
    base_config_list: EventServiceConfigList = proto_from_json_file(args.config, EventServiceConfigList())
    service_config_list = EventServiceConfigList()
    for cfg in base_config_list.configs:
        if cfg.port == 0: continue
        service_config_list.configs.append(cfg)

    event_manager = EventClientSubscriptionManager(config_list=service_config_list)

    oak_manager = OakManager()

    asyncio.create_task(event_manager.update_subscriptions())

    return {
        "event_manager": event_manager,
        "oak_manager": oak_manager,
        # Yield dict cannot be changed directly, but objects inside it can
        # So we use a sv item for all our non constant variables
        "sv": config.StateVars(),
    }


app = FastAPI(lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(tracks.router)
app.include_router(record.router)
app.include_router(follow.router)
app.include_router(linefollow.router)


# not sure why params are necessary but won't touch it in case the robot complains
# could use testing
def handle_sigterm(signum: Any, frame: Any) -> None:
    if oak_manager is not None:
        print("Received SIGTERM, shutting down oak manager...")
        oak_manager.shutdown()
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
    FULL_SERVICE_NAME = "filter"
    client: EventClient = event_manager.clients[FULL_SERVICE_NAME]

    await websocket.accept()

    disconnected = False

    async for _, msg in client.subscribe(
        SubscribeRequest(uri=Uri(path="/state", query=f"service_name={FULL_SERVICE_NAME}"), every_n=every_n),
        decode=True,
    ):
        try: await websocket.send_json(MessageToJson(msg))
        except WebSocketDisconnect:
            disconnected = True
            break

    if not disconnected: await websocket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the FastAPI server.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run the server in debug mode, serving the React app.",
    )
    # default value is the path on the amiga
    parser.add_argument(
        "--config",
        type=str,
        default="/opt/farmng/config.json",
        help="Path to the config file.",
    )

    PORT = config.PORT
    cli_args = parser.parse_args()
    if cli_args.debug:
        react_build_directory = Path(__file__).parent / ".." / "ts" / "dist"
        app.mount("/", StaticFiles(directory=str(react_build_directory.resolve()), html=True))

    uvicorn.run(app, host="0.0.0.0", port=PORT)  # noqa: S104
