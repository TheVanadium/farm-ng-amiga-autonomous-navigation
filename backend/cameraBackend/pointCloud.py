# Modified code from
# https://github.com/luxonis/depthai-experiments/blob/master/gen2-multiple-devices/rgbd-pointcloud-fusion/point_cloud_visualizer.py

import os
from typing import List

import numpy as np
import open3d as o3d

from .camera import Camera

from .pointCloudCompression import compress_pcd


class PointCloudFusion:
    """
    Fuse and manage point clouds from multiple Camera instances.

    Initializes with a list of Camera objects and provides methods to align,
    reset, save, and get point cloud fusion.

    Args:
        cameras (List[Camera]):
            List of Camera instances whose point clouds will be fused.

    Methods:
        align_point_clouds():
            Compute and save colored‐ICP alignment of all cameras.
        reset_alignment():
            Reset each camera's alignment matrix to identity matrix and save it.
        save_point_cloud():
            Update each camera, save individual and fused point cloud files to disk.
        get_point_cloud() -> o3d.geometry.PointCloud:
            Update cameras, fuse their point clouds, and return the result.
    """

    def __init__(self, cameras: List[Camera], POINTCLOUD_DATA_DIR: str):
        self._cameras = cameras
        self._POINTCLOUD_DATA_DIR = POINTCLOUD_DATA_DIR

    def align_point_clouds(self):
        voxel_radius = [0.04, 0.02, 0.01]
        max_iter = [50, 30, 14]

        reference_point_cloud = self._cameras[1].point_cloud  # arbitrary?

        # Figure out alignment for each camera relative to master camera
        for camera in self._cameras[1:]:
            for iter, radius in zip(max_iter, voxel_radius):
                target_down = reference_point_cloud.voxel_down_sample(radius)
                target_down.estimate_normals(
                    o3d.geometry.KDTreeSearchParamHybrid(radius=radius * 2, max_nn=30)
                )

                source_down = camera.point_cloud.voxel_down_sample(radius)
                source_down.estimate_normals(
                    o3d.geometry.KDTreeSearchParamHybrid(radius=radius * 2, max_nn=30)
                )

                result_icp = o3d.pipelines.registration.registration_colored_icp(
                    source_down,
                    target_down,
                    radius,
                    camera.alignment,
                    o3d.pipelines.registration.TransformationEstimationForColoredICP(),
                    o3d.pipelines.registration.ICPConvergenceCriteria(
                        relative_fitness=1e-6, relative_rmse=1e-6, max_iteration=iter
                    ),
                )

                camera.alignment = result_icp.transformation

            camera.save_point_cloud_alignment()

    def reset_alignment(self):
        for camera in self._cameras:
            camera.alignment = np.identity(4)
            camera.save_point_cloud_alignment()

    def save_point_cloud(self, line_name, row_number, capture_number):
        path = f"{self._POINTCLOUD_DATA_DIR}/{line_name}/row_{row_number}/capture_{capture_number}"
        if not os.path.exists(path):
            os.makedirs(path)
        for i, camera in enumerate(self._cameras):
            camera.update()
            camera_path = f"{path}/camera-{i}.drc"
            with open(camera_path, "wb") as f:
                f.write(compress_pcd(camera.point_cloud))
