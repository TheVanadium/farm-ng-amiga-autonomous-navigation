import cv2
import depthai as dai
from camera import Camera
from typing import List
from point_cloud_visualizer import PointCloudVisualizer

print("Starting")
device_infos = dai.Device.getAllAvailableDevices()
if len(device_infos) == 0:
    raise RuntimeError("No devices found!")
else:
    print("Found", len(device_infos), "devices")
    print(device_infos)

device_infos.sort(
    key=lambda x: x.getMxId(), reverse=True
)  # sort the cameras by their mxId

cameras: List[Camera] = []

for device_info in device_infos:
    if device_info.name == "10.95.76.10":
        continue
    cameras.append(
        Camera(device_info, len(cameras) + 1, show_video=True, show_point_cloud=False)
    )


PointCloudVisualizer(cameras)
