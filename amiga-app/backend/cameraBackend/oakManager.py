from multiprocessing import Queue
import signal
import sys
import os
from queue import Empty
from time import sleep
from typing import List

import depthai as dai

from cameraBackend.camera import Camera
from cameraBackend.pointCloud import PointCloudFusion

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Last digit of ip identifies the camera
# 0 = Oak0, etc
cameras: List[Camera] = []
cameraIps: list[str] = ["10.95.76.11", "10.95.76.12", "10.95.76.13"]
# STREAM_PORT_BASE + last 2 digits of ip identifies the port for streaming
STREAM_PORT_BASE: str = "50"

PIPELINE_FPS: int = 30
VIDEO_FPS: int = 20


def startCameras(queue: Queue, POINTCLOUD_DATA_DIR: str) -> None:
    """
    Initialize DepthAI cameras, set up point‐cloud fusion, and listen for control
    commands using a multiprocessing queue.

    This function performs the following steps:

      1. Registers a SIGTERM handler that will gracefully shut down all initialized
         cameras and exit the process.
      2. Queries all available DepthAI devices, skipping 10.95.76.10 (Oak0 is not used).
      3. For each device, creates a unique streaming port based on STREAM_PORT_BASE and
         the device’s last two IP digits, then creates and starts a Camera instance.
      4. Instantiates a PointCloudFusion manager for all cameras.
      5. Enters an infinite loop, polling the queue for command strings.

    Args:
        TODO: Update queue message parameters
        queue (multiprocessing.Queue):
            A queue for receiving control commands. Supported messages are:
              - "align_point_clouds"
              - "reset_alignment"
              - "save_point_cloud"
        POINTCLOUD_DATA_DIR (str):
            The directory to store point clouds to.

    Returns:
        None
    """

    # Register handler here so the while loop can be interrupted
    def handle_sigterm(signum, frame) -> None:
        print("Received SIGTERM, stopping oak manager")
        for camera in cameras:
            camera.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)

    device_infos = dai.Device.getAllAvailableDevices()
    device_infos.sort(key=lambda x: x.name, reverse=True)  # Sort by ip
    print(
        f"Found {len(device_infos)} devices: {[device_info.name for device_info in device_infos]}"
    )
    for device_info in device_infos:
        if device_info.name == "10.95.76.10":  # Not using Oak0
            continue
        print(f"Initializing camera {device_info.name}")
        port = int(STREAM_PORT_BASE + device_info.name[-2:])
        # Initialize camera
        try:
            cameras.append(Camera(device_info, port, PIPELINE_FPS, VIDEO_FPS))
        except Exception as e:
            print(f"Failed to initialize camera {device_info.name}: {e}")
        sleep(2)  # BUG: problem with DepthAI? Can't initialize cameras all at once

    pointCloudFusion = PointCloudFusion(cameras, POINTCLOUD_DATA_DIR)

    if queue != None:
        # Difference between calibration and alignment is that calibration
        # defines initial camera positioning and alignment refines the
        # positioning. Calibration requires calibration pattern and is
        # mandatory. Alignment is optional and can be done on the fly.
        while True:
            if os.getppid() == 1:  # 1 means parent is gone
                sys.exit(1)
            try:
                msg = queue.get(timeout=0.1)  # Blocking
                action = msg.get("action", "No action")
                if action == "align_point_clouds":
                    pointCloudFusion.align_point_clouds()
                elif action == "reset_alignment":
                    pointCloudFusion.reset_alignment()
                elif action == "save_point_cloud":
                    line_name = msg.get("line_name", "X")
                    row_number = msg.get("row_number", "X")
                    capture_number = msg.get("capture_number", "X")
                    pointCloudFusion.save_point_cloud(
                        line_name, row_number, capture_number
                    )
                else:
                    print(f"Unknown message: {msg}")
                    continue

            except Empty:
                continue


# if __name__ == "__main__":
#     q = Queue()
#     startCameras(q, "")
