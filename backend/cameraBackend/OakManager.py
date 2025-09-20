from multiprocessing import Queue, Process
import signal, sys, os
from queue import Empty
from time import sleep
from typing import List
import depthai as dai
from cameraBackend.camera import Camera
from cameraBackend.pointCloudCompression import compress_pcd
from config import POINTCLOUD_DATA_DIR
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

class OakManager:
    def __init__(self, queue: Queue = Queue(), cameras: List[Camera] = [], stream_port_base: str = "50", pipeline_fps: int = 30,
                 video_fps: int = 20) -> None:
        self.queue = queue
        self.cameras = cameras
        self.STREAM_PORT_BASE = stream_port_base
        self.PIPELINE_FPS = pipeline_fps
        self.VIDEO_FPS = video_fps
        self.process = Process(target=self.startCameras, daemon=True)
        self.process.start()

    def startCameras(self) -> None:
        def handle_sigterm(signum, frame) -> None:
            print("Received SIGTERM, stopping oak manager")
            for camera in self.cameras:
                camera.shutdown()
            sys.exit(0)
        signal.signal(signal.SIGTERM, handle_sigterm)
        device_infos = dai.Device.getAllAvailableDevices()
        print(f"Found {len(device_infos)} devices: {[device_info.name for device_info in device_infos]}")
        for device_info in device_infos:
            if device_info.name == "10.95.76.10": continue # this ip is oak0, which we aren't using
            print(f"Initializing camera {device_info.name}")
            port = int(self.STREAM_PORT_BASE + device_info.name[-2:])
            try: self.cameras.append(Camera(device_info, port, self.PIPELINE_FPS, self.VIDEO_FPS))
            except Exception as e: print(f"Failed to initialize camera {device_info.name}: {e}")
            sleep(2)  # BUG: problem with DepthAI? Can't initialize cameras all at once
        while True:
            if os.getppid() == 1: sys.exit(1) # 1 means parent is gone
            try:
                msg = self.queue.get(timeout=0.1)  # Blocking
                action = msg.get("action", "No action")
                if action != "save_point_cloud":
                    print(f"Unknown message: {msg}")
                    continue
                line_name = msg.get("line_name", "X")
                row_number = msg.get("row_number", "X")
                capture_number = msg.get("capture_number", "X")
                path = f"{POINTCLOUD_DATA_DIR}/{line_name}/row_{row_number}/capture_{capture_number}"
                if not os.path.exists(path): os.makedirs(path)
                for i, camera in enumerate(self.cameras):
                    camera.update()
                    camera_path = f"{path}/camera-{i}.drc"
                    with open(camera_path, "wb") as f: f.write(compress_pcd(camera.point_cloud))
            except Empty: continue
