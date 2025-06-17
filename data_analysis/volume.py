import open3d as o3d
import numpy as np
from typing import Dict, List

# These ips can't change and belong to each camera
cameras = ["10.95.76.11", "10.95.76.12", "10.95.76.13"]


def get_camera_transforms() -> Dict[str, List[np.ndarray]]:
    """
    Summary:
        Helper function for correct_points(). Retrieves camera transforms.

    Returns:
        Dict[str, List[np.ndarray]]: Camera ip, camera transform matrices
    """

    # TODO: This shouldn't be hardcoded. Fix this when integrating analysis into the app
    cal_dir = "./calibration_data"
    transforms = {}
    for camera in cameras:
        calibration_path = f"{cal_dir}/extrinsics_{camera}.npz"
        calibration_data = np.load(calibration_path)
        transform_mat = calibration_data["cam_to_world"]
        rot_mat = transform_mat[:3, :3]
        trans_vec = (transform_mat[:3, 3] * 1000).reshape((1, 3))
        transforms[camera] = [rot_mat, trans_vec]
    return transforms


transforms = get_camera_transforms()


def preprocess_points(
    cam_transform: List[np.ndarray],
    point_cloud: o3d.geometry.PointCloud,
    z_correction_percentiles: tuple[float, float],
) -> o3d.geometry.PointCloud:
    """
    Summary:
        Helper function for height_volume_estimate(). Prepares the raw data
        by transforming the point clouds to the correct position and does minor filtering.
        Assumes point_cloud is currently in world space.

    Args:
        cam_transform (List[np.ndarray]): numpy transform matrices
        point_cloud (o3d.geometry.PointCloud): open3d point cloud object
        z_correction_percentiles (tuple[float, float]): Z percentiles to filter points

    Returns:
        o3d.geometry.PointCloud: Preprocessed point cloud
    """
    rot_mat, trans_vec = cam_transform

    points = np.asarray(point_cloud.points)
    colors = np.asarray(point_cloud.colors)
    num_points = points.shape[0]

    # To move points to camera space, subtract transation vector and multiply by rotation matrix
    points -= trans_vec
    points = points @ rot_mat

    # Filter out near and far z points to remove noise and irrelevent data
    height_sort = np.argsort(points[:, 2])
    points = points[height_sort]
    colors = colors[height_sort]
    z_lower, z_upper = z_correction_percentiles
    upper_ind = round(num_points * z_upper)
    lower_ind = round(num_points * z_lower)
    if lower_ind < 0:
        z_lower = float("-inf")
    else:
        z_lower = points[round(num_points * z_lower), 2]
    if upper_ind >= num_points:
        z_upper = float("inf")
    else:
        z_upper = points[round(num_points * z_upper), 2]
    z_coords = points[:, 2]
    z_filter = (z_coords > z_lower) & (z_coords < z_upper)
    points = points[z_filter]
    colors = colors[z_filter]

    # To return to world space, multiply by inverse rotation matrix and subtract translation vector
    # We subtract again because the translation vector is lives in camera space
    return_world = True
    if return_world:
        points = points @ rot_mat.T
        points -= trans_vec
    point_cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
    point_cloud.colors = o3d.utility.Vector3dVector(colors)

    return point_cloud


def height_volume_estimate(pc_dir: str) -> float:
    """
    Summary:
        Uses average height of the crop to estimate volume using a power law

    Args:
        pc_dir (str): Directory of a point cloud capture

    Returns:
        float: Estimated volume
    """

    point_cloud = None
    center_point_cloud = None

    # Iterate over each camera to create combined point cloud
    for camera in cameras:
        is_center = camera == "10.95.76.12"
        if is_center:
            z_correction_percentiles = 0.05, 0.99
        else:
            z_correction_percentiles = 0.01, 0.95

        pc_path = f"{pc_dir}/{camera}.ply"
        curr_pc = o3d.io.read_point_cloud(pc_path)
        curr_pc = preprocess_points(
            transforms[camera], curr_pc, z_correction_percentiles
        )
        if is_center:
            center_point_cloud = curr_pc
        if point_cloud is None:
            point_cloud = curr_pc
        else:
            point_cloud += curr_pc

    center_points = np.asarray(center_point_cloud.points)
    average_center_z = np.mean(center_points[:, 2])

    all_points = np.asarray(point_cloud.points)
    ground_z_level = np.min(all_points[:, 2])

    z_diff = average_center_z - ground_z_level

    # Cilantro was cut approx 300mm above ground level
    cilantro_height_offset = 300
    average_height = z_diff - cilantro_height_offset

    # We will assume the density of the cilantro is not linear with height, so
    # We apply a density exponent to correct for this
    density_exponent = 3.83
    volume_approximator = average_height**density_exponent

    visual = False
    if visual:
        voxel_size = 2
        voxel_grid = o3d.geometry.VoxelGrid.create_from_point_cloud(
            point_cloud, voxel_size=voxel_size
        )
        vis = o3d.visualization.Visualizer()  # type: ignore
        vis.create_window(height=900, width=1600)
        vis.add_geometry(voxel_grid)
        vis.run()
    print(volume_approximator)

    return volume_approximator
