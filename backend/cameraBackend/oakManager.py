from multiprocessing import Queue
import signal, sys, os
from queue import Empty
from time import sleep
from typing import List
import depthai as dai
import cv2
from cameraBackend.camera import Camera
from cameraBackend.pointCloudCompression import compress_pcd
from config import POINTCLOUD_DATA_DIR
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Last digit of ip identifies the camera
# 0 = Oak0, etc
cameras: List[Camera] = []
# STREAM_PORT_BASE + last 2 digits of ip identifies the port for streaming
STREAM_PORT_BASE: str = "50"
PIPELINE_FPS: int = 30
VIDEO_FPS: int = 20


def startCameras(queue: Queue) -> None:
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

    Difference between calibration and alignment is that calibration
    defines initial camera positioning and alignment refines the
    positioning. Calibration requires calibration pattern and is
    mandatory. Alignment is optional and can be done on the fly.  
    
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
    print(f"Found {len(device_infos)} devices: {[device_info.name for device_info in device_infos]}")
    for device_info in device_infos:
        if device_info.name == "10.95.76.10": continue # this ip is oak0, which we aren't using
        print(f"Initializing camera {device_info.name}")
        port = int(STREAM_PORT_BASE + device_info.name[-2:])
        try: cameras.append(Camera(device_info, port, PIPELINE_FPS, VIDEO_FPS))
        except Exception as e: print(f"Failed to initialize camera {device_info.name}: {e}")
        sleep(2)  # BUG: problem with DepthAI? Can't initialize cameras all at once
    if queue == None: return
    while True:
        if os.getppid() == 1: sys.exit(1) # 1 means parent is gone
        try:
            msg = queue.get(timeout=0.1)  # Blocking
            action = msg.get("action", "No action")
            if action is not "save_point_cloud":
                print(f"Unknown message: {msg}")
                continue
            line_name = msg.get("line_name", "X")
            row_number = msg.get("row_number", "X")
            capture_number = msg.get("capture_number", "X")
            path = f"{POINTCLOUD_DATA_DIR}/{line_name}/row_{row_number}/capture_{capture_number}"
            if not os.path.exists(path): os.makedirs(path)
            for i, camera in enumerate(cameras):
                camera.update()
                camera_path = f"{path}/camera-{i}.drc"
                with open(camera_path, "wb") as f: f.write(compress_pcd(camera.point_cloud))
                rgb_camera_path = f"{path}/rgb-camera-{i}.png"
                cv2.imwrite(rgb_camera_path, cv2.cvtColor(camera.bgr_image, cv2.COLOR_BGR2RGB))
        except Empty: continue
