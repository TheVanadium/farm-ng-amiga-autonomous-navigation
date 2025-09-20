from multiprocessing import Queue, Process
import signal, sys, os, threading, cv2, DracoPy
import numpy as np, open3d as o3d, depthai as dai
from queue import Empty
from time import sleep
from typing import List, Optional
from datetime import timedelta
from config import POINTCLOUD_DATA_DIR, CALIBRATION_DATA_DIR, PORT
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

class Camera:
    """
    Manages a DepthAI camera device, captures RGB-D point clouds, and hosts
    an HTTP MJPEG stream.

    On initialization, builds and starts a DepthAI pipeline with:

      - A VideoEncoder node to produce MJPEG frames, forwarded to a
        background streaming server process on localhost at the given TCP port.
      - A ToF node configured to emit depth frames.
      - An RGB camera producing ISP frames at TOF_FPS for color data.
      - Queues to receive video, image, and depth frames from the camera.

    Calibration data (intrinsics, extrinsics, and alignment) are loaded from disk
    to project depth + color into a Open3D PointCloud.

    Args:
        device_info (dai.DeviceInfo):
            DepthAI object containing information about the camera.
        stream_port (int):
            TCP port on which to serve the MJPEG video stream. Has to be unique.
        PIPELINE_FPS (int):
            Frames per second for the pipeline.
        VIDEO_FPS (int):
            Frames per second for the MJPEG stream.

    Attributes:
        _camera_ip (str):
            Network address of the camera. Only for identification.
        stream_port (int):
            Port for the MJPEG HTTP server.
        PIPELINE_FPS (int):
            Pipeline frame rate.
        VIDEO_FPS (int):
            Video frame rate.
        _pipeline (dai.Pipeline):
            DepthAI pipeline to be uploaded to the camera.
        _device (dai.Device):
            Active DepthAI device instance.
        _image_queue, _depth_queue, _video_queue (dai.Queue):
            Non-blocking queues for frames.
        server_stream_queue (multiprocessing.Queue):
            IPC queue feeding the streaming server.
        _image_frame (ndarray):
            Latest RGB frame.
        _depth_frame (ndarray):
            Latest depth frame.
        point_cloud (o3d.geometry.PointCloud):
            Latest fused point cloud.
        streamingServer (multiprocessing.Process):
            Background MJPEG server process.

    Methods:
        _updateVideoQueue():
            Callback invoked on new encoded video frames; enqueues raw JPEG bytes
            into the server_stream_queue for HTTP serving.
        update():
            Polls image & depth queues, synchronizes frames, converts to point cloud.
        _rgbd_to_point_cloud(depth_frame, image_frame, downsample=False, remove_noise=False):
            Builds an Open3D PointCloud from aligned RGB + depth data with optional
            voxel-downsampling and denoising.
        save_point_cloud_alignment():
            Saves the current 'alignment' matrix to disk for later reuse.
        shutdown():
            Gracefully terminates the streaming server process and closes the device.
    """

    def __init__(
        self,
        device_info: dai.DeviceInfo,
        stream_port: int,
        PIPELINE_FPS: int,
        VIDEO_FPS: int,
    ):
        self.PIPELINE_FPS = PIPELINE_FPS
        self.VIDEO_FPS = VIDEO_FPS

        self._camera_ip: str = device_info.name
        self.stream_port: int = stream_port
        self._create_pipeline()
        self._device = dai.Device(self.pipeline, device_info)  # Initialize camera
        self._device.setIrLaserDotProjectorBrightness(0)  # Not using active stereo
        self._device.setIrFloodLightIntensity(0)

        self._device_info = device_info

        self._video_queue: dai.DataOutputQueue = self._device.getOutputQueue(
            name="video", maxSize=2, blocking=False  # pyright: ignore[reportCallIssue]
        )

        self.output_queue = self._device.getOutputQueue(
            name="out", maxSize=4, blocking=False  # pyright: ignore[reportCallIssue]
        )

        self.point_cloud = o3d.geometry.PointCloud()

        self._load_calibration()

        print("=== Connected to " + self._device_info.name)

        # Start streams as seperate thread
        self._http_streaming_server: Optional[ThreadingHTTPServer] = None
        self.streamingServerThread = threading.Thread(
            target=self.start_streaming_server, daemon=True
        )
        self.streamingServerThread.start()
        print(f"Starting streaming server for camera {device_info.name}")

    def shutdown(self):
        if self._http_streaming_server:
            print("Shutting down HTTP server...")
            self._http_streaming_server.shutdown()
        if self.streamingServerThread.is_alive():
            self.streamingServerThread.join(timeout=5)
        self._device.close()
        print("=== Closed " + self._device_info.name)

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            return

    def _load_calibration(self):
        path = f"{CALIBRATION_DATA_DIR}/extrinsics_{self._camera_ip}.npz"
        try:
            extrinsics = np.load(path)
            self.cam_to_world = extrinsics["cam_to_world"]
            self.world_to_cam = extrinsics["world_to_cam"]
            print(f"Calibration data for camera {self._camera_ip} loaded successfully.")
        except Exception:
            # TODO: figure out how to handle b/c calibration data is mandatory
            # raise RuntimeError(f"Could not load calibration data for camera {self.camera_ip} from {path}!")
            print(
                f"ERROR: No extrinsic calibration data for camera {self._camera_ip} found."
            )

        try:
            self.alignment = np.load(
                f"{CALIBRATION_DATA_DIR}/alignment_{self._camera_ip}.npy"
            )
            print(f"Alignment data for camera {self._camera_ip} loaded successfully.")
        except Exception:
            print(f"WARNING: No alignment data for camera {self._camera_ip} found.")
            self.alignment = np.eye(4)  # Default to no alignment correction

        flip_z = np.eye(4)
        flip_z[2, 2] = -1.0
        self.transform_matrix = self.cam_to_world @ self.alignment @ flip_z
        self.transform_matrix[:3, 3] *= 1000.0  # Convert from meters to mm

        # print(self.pinhole_camera_intrinsic)

    def save_point_cloud_alignment(self):
        np.save(
            f"{CALIBRATION_DATA_DIR}/alignment_{self._camera_ip}.npy", self.alignment
        )
        print(f"Saved alignment for camera {self._camera_ip}.")

    def _create_pipeline(self):
        pipeline = dai.Pipeline()
        # Define sources and outputs
        camRgb = pipeline.create(dai.node.ColorCamera)
        tof = pipeline.create(dai.node.ToF)
        camTof = pipeline.create(dai.node.Camera)
        sync = pipeline.create(dai.node.Sync)
        align = pipeline.create(dai.node.ImageAlign)
        out = pipeline.create(dai.node.XLinkOut)
        pointcloud = pipeline.create(dai.node.PointCloud)

        # ToF settings
        camTof.setFps(self.PIPELINE_FPS * 2)
        camTof.setBoardSocket(dai.CameraBoardSocket.CAM_A)

        tofConfig = tof.initialConfig.get()
        # choose a median filter or use none - using the median filter improves the pointcloud but causes discretization of the data
        tofConfig.enableOpticalCorrection = True
        tofConfig.enablePhaseShuffleTemporalFilter = True
        tofConfig.phaseUnwrappingLevel = 0
        tofConfig.phaseUnwrapErrorThreshold = 300
        tofConfig.median = dai.MedianFilter.KERNEL_3x3
        # tofConfig.median = dai.MedianFilter.KERNEL_5x5
        # tofConfig.median = dai.MedianFilter.KERNEL_7x7
        tof.initialConfig.set(tofConfig)

        # rgb settings
        camRgb.setBoardSocket(dai.CameraBoardSocket.CAM_C)
        camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_800_P)
        camRgb.setFps(self.PIPELINE_FPS)
        camRgb.setIspScale(1, 2)

        out.setStreamName("out")

        sync.setSyncThreshold(timedelta(seconds=(1 / self.PIPELINE_FPS)))

        # Linking
        camRgb.isp.link(sync.inputs["bgr"])
        camTof.raw.link(tof.input)
        tof.depth.link(align.input)
        # align.outputAligned.link(sync.inputs["depth_aligned"])
        align.outputAligned.link(pointcloud.inputDepth)
        sync.inputs["bgr"].setBlocking(False)
        camRgb.isp.link(align.inputAlignTo)
        pointcloud.outputPointCloud.link(sync.inputs["pcl"])
        sync.out.link(out.input)
        out.setStreamName("out")

        # Video encoder (MJPEG) for frontend
        video_enc = pipeline.create(dai.node.VideoEncoder)
        video_enc.setDefaultProfilePreset(
            self.PIPELINE_FPS, dai.VideoEncoderProperties.Profile.MJPEG
        )
        video_enc.setFrameRate(self.PIPELINE_FPS)

        # Link video encoder output to XLinkOut("video")
        xout_video = pipeline.createXLinkOut()
        xout_video.setStreamName("video")
        xout_video.setFpsLimit(self.VIDEO_FPS)
        xout_video.input.setBlocking(False)
        xout_video.input.setQueueSize(1)
        video_enc.bitstream.link(xout_video.input)
        video_enc.setQuality(50)
        camRgb.video.link(video_enc.input)

        self.image_size = camRgb.getIspSize()
        self.pipeline = pipeline

    def update(self):
        # we need to type iignore this because depthAI's output queue is generic and thus ambiguous
        output_packet = self.output_queue.get()

        rgb = cv2.cvtColor(output_packet["bgr"].getCvFrame(), cv2.COLOR_BGR2RGB) # type: ignore
        colors = rgb.reshape(-1, 3).astype(np.float64) / 255.0

        raw_points = output_packet["pcl"].getPoints().astype(np.float64) # type: ignore

        # R = rotation matrix , t = translation vector
        R, t = self.transform_matrix[:3, :3], self.transform_matrix[:3, 3]
        transformed_points = raw_points @ R.T - t.reshape((1, 3))

        self.point_cloud.points = o3d.utility.Vector3dVector(transformed_points)
        self.point_cloud.colors = o3d.utility.Vector3dVector(colors)

    def make_handler(self, frame_queue: dai.DataOutputQueue):
        class MJPEGHandler(BaseHTTPRequestHandler):
            def end_headers(self):
                self.send_header(
                    "Access-Control-Allow-Origin", f"http://0.0.0.0:{PORT}"
                )
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                super().end_headers()

            def do_OPTIONS(self):
                self.send_response(204)  # No Content
                self.end_headers()

            def do_GET(self):
                if self.path != "/rgb":
                    self.send_response(404)
                    self.end_headers()
                    return

                try:
                    self.send_response(200)
                    self.send_header(
                        "Content-Type",
                        "multipart/x-mixed-replace; boundary=--jpgboundary",
                    )
                    self.end_headers()

                    while True:
                        frame = frame_queue.get().getData().tobytes()  # type: ignore
                        boundary = b"--jpgboundary\r\n"
                        header = (
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(frame)).encode() + b"\r\n\r\n"
                        )
                        self.wfile.write(boundary + header + frame + b"\r\n")
                        self.wfile.flush()

                except Exception:
                    return

        return MJPEGHandler

    def start_streaming_server(self):
        self._http_streaming_server = ThreadingHTTPServer(
            ("", self.stream_port), self.make_handler(self._video_queue)
        )
        print(f"Starting RGB stream at 127.0.0.1:{self.stream_port}")
        self._http_streaming_server.serve_forever()
        self._http_streaming_server.server_close()
        print(f"RGB stream at 127.0.0.1:{self.stream_port} stopped")


def compress_pcd(pcd: o3d.geometry.PointCloud) -> bytes:
    """Compresses an open3d PointCloud with Draco

    Args:
        pcd (o3d.geometry.PointCloud): The point cloud to compress.

    Returns:
        bytes: The compressed point cloud in Draco format.
    """

    points = np.asarray(pcd.points, dtype=np.float32)
    colors = (np.asarray(pcd.colors) * 255).astype(np.uint8)
    return DracoPy.encode(points, colors=colors)


def decompress_drc(draco_binary: bytes) -> o3d.geometry.PointCloud:
    """Decompresses a Draco binary to an open3d PointCloud
    Args:
        draco_binary (bytes): The compressed point cloud in Draco format.

    Returns:
        o3d.geometry.PointCloud: The decompressed point cloud.

    Raises:
        ValueError: If the binary does not contain points or colors when
            decoded with DracoPy.
    """
    decoded_drc = DracoPy.decode(draco_binary)
    if not hasattr(decoded_drc, "points"):
        raise ValueError("Input missing points")
    if not hasattr(decoded_drc, "colors"):
        raise ValueError("Input missing colors")

    decompressed_points = o3d.utility.Vector3dVector(np.asarray(decoded_drc.points))
    decompressed_colors = o3d.utility.Vector3dVector(
        np.asarray(decoded_drc.colors) / 255
    )

    decompressed_pcd = o3d.geometry.PointCloud(decompressed_points)
    decompressed_pcd.colors = decompressed_colors
    return decompressed_pcd

class OakManager:
    def __init__(self, queue: Queue = Queue(), cameras: List[Camera] = [], stream_port_base: str = "50", pipeline_fps: int = 30,
                 video_fps: int = 20) -> None:
        self.queue, self.cameras = queue, cameras
        self.STREAM_PORT_BASE, self.PIPELINE_FPS, self.VIDEO_FPS = stream_port_base, pipeline_fps, video_fps

        device_infos = dai.Device.getAllAvailableDevices()
        print(f"Found {len(device_infos)} devices: {[device_info.name for device_info in device_infos]}")
        for device_info in device_infos:
            if device_info.name == "10.95.76.10": continue # this ip is oak0, which we aren't using
            print(f"Initializing camera {device_info.name}")
            port = int(self.STREAM_PORT_BASE + device_info.name[-2:]) # this is how our cameras happen to be named
            try: self.cameras.append(Camera(device_info, port, self.PIPELINE_FPS, self.VIDEO_FPS))
            except Exception as e: print(f"Failed to initialize camera {device_info.name}: {e}")
            sleep(2)  # BUG: problem with DepthAI? Can't initialize cameras all at once

        self.process = Process(target=self.startCameras, daemon=True)
        self.process.start()

    def startCameras(self) -> None:
        def handle_sigterm(signum, frame) -> None:
            print("Received SIGTERM, stopping oak manager")
            for camera in self.cameras: camera.shutdown()
            sys.exit(0)
        signal.signal(signal.SIGTERM, handle_sigterm)
        while True:
            if os.getppid() == 1: sys.exit(1) # 1 means parent is gone
            try: msg = self.queue.get(timeout=0.1)  # Blocking
            except Empty: continue
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
