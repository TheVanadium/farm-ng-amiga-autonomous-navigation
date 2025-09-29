# Modified code from
# https://github.com/luxonis/depthai-experiments/blob/master/gen2-multiple-devices/rgbd-pointcloud-fusion/camera.py
# https://github.com/luxonis/depthai-python/blob/main/examples/ToF/tof_depth.py

import sys
import os
import time
from datetime import timedelta
import datetime
import threading
from typing import Optional

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import cv2
import depthai as dai
import numpy as np
import open3d as o3d

from config import CALIBRATION_DATA_DIR
from config import PORT


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
        _sync_queue (SyncQueue):
            Helper to synchronize depth + image pairs.
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

        self.rgb_image: Optional[np.ndarray] = None # Unsure of image size to preallocate

        self._load_calibration()

        print("=== Connected to " + self._device_info.name)

        # Start streams as seperate thread
        self._http_streaming_server = None
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
        except:
            return

    def _load_calibration(self):
        path = f"{CALIBRATION_DATA_DIR}/extrinsics_{self._camera_ip}.npz"
        try:
            extrinsics = np.load(path)
            self.cam_to_world = extrinsics["cam_to_world"]
            self.world_to_cam = extrinsics["world_to_cam"]
            print(f"Calibration data for camera {self._camera_ip} loaded successfully.")
        except:
            # TODO: figure out how to handle b/c calibration data is mandatory
            # raise RuntimeError(f"Could not load calibration data for camera {self.camera_ip} from {path}!")
            print(
                f"ERROR: No extrinsic calibration data for camera {self._camera_ip} found."
            )

        # calibration = self._device.readCalibration()
        # intrinsics = calibration.getCameraIntrinsics(
        #     # TODO: Figure out if this is the correct socket
        #     dai.CameraBoardSocket.CAM_C,
        #     dai.Size2f(*self.image_size),  # type: ignore
        # )

        # self.pinhole_camera_intrinsic = o3d.camera.PinholeCameraIntrinsic(
        #     *self.image_size,
        #     intrinsics[0][0],
        #     intrinsics[1][1],
        #     intrinsics[0][2],
        #     intrinsics[1][2],
        # )

        try:
            self.alignment = np.load(
                f"{CALIBRATION_DATA_DIR}/alignment_{self._camera_ip}.npy"
            )
            print(f"Alignment data for camera {self._camera_ip} loaded successfully.")
        except:
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

        #
        # # Time‐of‐flight / depth pipeline
        # tof = pipeline.create(dai.node.ToF)
        # # Apply ToF settings
        # cfg = tof.initialConfig.get()
        # cfg.enableOpticalCorrection = True
        # cfg.enablePhaseShuffleTemporalFilter = True
        # cfg.phaseUnwrappingLevel = 1
        # cfg.phaseUnwrapErrorThreshold = 200
        #
        # # Create ToF config
        # xin_tof_cfg = pipeline.create(dai.node.XLinkIn)
        # xin_tof_cfg.setStreamName("tofConfig")
        #
        #
        # xin_tof_cfg.out.link(tof.inputConfig)
        #
        # tof.initialConfig.set(cfg)
        #
        # # Raw ToF camera feed
        # cam_tof = pipeline.create(dai.node.Camera)
        # cam_tof.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        # cam_tof.setFps(self.PIPELINE_FPS * 2)  # ToF outputs at half this rate
        # cam_tof.raw.link(tof.input)
        #
        # # ToF to depth output
        # xout_depth = pipeline.create(dai.node.XLinkOut)
        # xout_depth.setStreamName("depth")
        # tof.depth.link(xout_depth.input)
        #
        # # RGB camera
        # # cam_rgb = pipeline.createColorCamera()
        # cam_rgb = pipeline.create(dai.node.ColorCamera)
        # cam_rgb.setBoardSocket(dai.CameraBoardSocket.CAM_C)
        # cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_800_P)
        # cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)
        # cam_rgb.setIspScale(1, 2)
        # cam_rgb.setFps(self.PIPELINE_FPS)
        # cam_rgb.setVideoSize(640, 400)
        #
        # # RGB image outputs
        # xout_image = pipeline.createXLinkOut()
        # xout_image.setStreamName("image")
        # cam_rgb.isp.link(xout_image.input)
        # camRgb.video.link(video_enc.input)

        # self.image_size = cam_rgb.getIspSize()
        self.image_size = camRgb.getIspSize()
        self.pipeline = pipeline

    def update(self):
        # for queue in [self._depth_queue, self._image_queue]:
        #     new_frames = queue.tryGetAll()
        #     if new_frames is not None:
        #         for new_frame in new_frames:
        #             self._sync_queue.add(queue.getName(), new_frame)
        #
        # frame_sync = self._sync_queue.get()
        # if frame_sync is None:
        #     return
        #
        # self._depth_frame = frame_sync["depth"].getFrame()
        # self._image_frame = frame_sync["image"].getCvFrame()
        # rgb = cv2.cvtColor(self._image_frame, cv2.COLOR_BGR2RGB)
        # self._rgbd_to_point_cloud(self._depth_frame, rgb)

        output_packet = self.output_queue.get()

        rgb = cv2.cvtColor(output_packet["bgr"].getCvFrame(), cv2.COLOR_BGR2RGB)
        colors = rgb.reshape(-1, 3).astype(np.float64) / 255.0

        raw_points = output_packet["pcl"].getPoints().astype(np.float64)

        # R = rotation matrix , t = translation vector
        R, t = self.transform_matrix[:3, :3], self.transform_matrix[:3, 3]
        transformed_points = raw_points @ R.T - t.reshape((1, 3))

        self.point_cloud.points = o3d.utility.Vector3dVector(transformed_points)
        self.point_cloud.colors = o3d.utility.Vector3dVector(colors)
        self.rgb_image = rgb

    # def _rgbd_to_point_cloud(
    #     self, depth_frame, image_frame, downsample=False, remove_noise=False
    # ):
    #     depth_frame = depth_frame[:400, :]  # TODO: Check if this is correct
    #     rgb_o3d = o3d.geometry.Image(image_frame)
    #     df = np.copy(depth_frame).astype(np.float32)
    #     # df -= 20
    #     depth_o3d = o3d.geometry.Image(df)
    #     rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
    #         rgb_o3d, depth_o3d, convert_rgb_to_intensity=(len(image_frame.shape) != 3)
    #     )
    #
    #     point_cloud = o3d.geometry.PointCloud.create_from_rgbd_image(
    #         rgbd_image, self.pinhole_camera_intrinsic, self.world_to_cam
    #     )
    #
    #     print(depth_frame)
    #     print(rgb_o3d)
    #     print(len(point_cloud.points))
    #
    #     if downsample:
    #         point_cloud = point_cloud.voxel_down_sample(voxel_size=0.01)
    #
    #     if remove_noise:
    #         point_cloud = point_cloud.remove_statistical_outlier(
    #             nb_neighbors=30, std_ratio=0.1
    #         )[0]
    #
    #     self.point_cloud.points = point_cloud.points
    #     self.point_cloud.colors = point_cloud.colors
    #
    #     # correct upside down z axis
    #     T = np.eye(4)
    #     T[2, 2] = -1
    #     self.point_cloud.transform(T)
    #
    #     # apply point cloud alignment transform
    #     self.point_cloud.transform(self.alignment)
    #
    #     return self.point_cloud

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
