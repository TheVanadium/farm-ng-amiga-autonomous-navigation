import os
import open3d as o3d
import numpy as np
from scipy.stats import pearsonr
from typing import TypeAlias
import matplotlib.pyplot as plt
import json


def estimate_volume(
    point_cloud: o3d.geometry.PointCloud,
) -> tuple[float, float, o3d.geometry.PointCloud]:
    """_summary_ Estimate the volume of the point cloud

    Args:
        point_cloud (o3d.geometry.PointCloud):

    Returns:
        tuple[float, float, o3d.geometry.PointCloud]: Estimated volume, Percentage of points filtered, Bounded PointCloud
    """
    colors = np.asarray(point_cloud.colors)
    point_cloud = np.asarray(point_cloud.points)

    height_sort = np.argsort(point_cloud[:, 2])
    point_cloud = point_cloud[height_sort]
    colors = colors[height_sort]

    num_points = len(point_cloud)

    # Bounding box parameters
    # z_lower = point_cloud[round(num_points * .25), 2]
    # z_upper = point_cloud[round(num_points * .95), 2]
    z_lower = point_cloud[0, 2]
    z_upper = point_cloud[-1, 2]
    x_lower = -250
    x_upper = 450
    y_lower = -270
    y_upper = 330

    x_coords = point_cloud[:, 0]
    y_coords = point_cloud[:, 1]
    z_coords = point_cloud[:, 2]
    z_filter = (z_lower < z_coords) & (z_coords < z_upper)
    x_filter = (x_lower < x_coords) & (x_coords < x_upper)
    y_filter = (y_lower < y_coords) & (y_coords < y_upper)

    box_filter = z_filter & x_filter & y_filter
    filtered_area = (x_upper - x_lower) * (y_upper - y_lower)

    point_cloud = point_cloud[box_filter]
    colors = colors[box_filter]

    average_z = np.mean(point_cloud[:, 2])
    average_height = z_upper - average_z

    volume_estimate = average_height * filtered_area / 1000  # cm^3

    percent_size_change = (num_points - len(point_cloud)) / num_points

    point_cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(point_cloud))
    point_cloud.colors = o3d.utility.Vector3dVector(colors)

    return volume_estimate, percent_size_change, point_cloud


cameras = ["10.95.76.11", "10.95.76.12", "10.95.76.13"]


def get_camera_transforms():
    cal_dir = "./calibration_data"
    transforms = {}
    for camera in cameras:
        cal_path = f"{cal_dir}/extrinsics_{camera}.npz"
        cal_data = np.load(cal_path)
        transform_mat = cal_data["cam_to_world"]
        rot_mat = transform_mat[:3, :3]
        trans_vec = (transform_mat[:3, 3] * 1000).reshape((1, 3))
        transforms[camera] = [rot_mat, trans_vec]
    return transforms


transforms = get_camera_transforms()


def correct_points(cam_transform, point_cloud, z_correction_percentiles):
    rot_mat, trans_vec = cam_transform
    points = np.asarray(point_cloud.points)
    colors = np.asarray(point_cloud.colors)
    num_points = points.shape[0]
    # Because we messed up in the point cloud combining portion of our project,
    # In order to return the points to camera space, we must subtract trans vec and multiply by rotation matrix
    points -= trans_vec
    points = points @ rot_mat
    # Now that all points are in camera space, we will filter out near and far pixels
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

    # Now to get back to world space, we multiply by inverse rotation matrix and subtract trans vec AGAIN
    return_world = True
    if return_world:
        points = points @ rot_mat.T
        points -= trans_vec
    point_cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
    point_cloud.colors = o3d.utility.Vector3dVector(colors)

    return point_cloud


def estimate_volume(pc_dir) -> float:
    point_cloud = None
    center_point_cloud = None
    for camera in cameras:
        is_center = camera == "10.95.76.12"
        if is_center:
            z_correction_percentiles = 0.05, 0.99
        else:
            z_correction_percentiles = 0.01, 0.95

        pc_path = f"{pc_dir}/{camera}.ply"
        curr_pc = o3d.io.read_point_cloud(pc_path)
        curr_pc = correct_points(transforms[camera], curr_pc, z_correction_percentiles)
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

    visual = True
    if visual:
        voxel_size = 2
        voxel_grid = o3d.geometry.VoxelGrid.create_from_point_cloud(
            point_cloud, voxel_size=voxel_size
        )
        vis = o3d.visualization.Visualizer()
        vis.create_window(height=900, width=1600)
        vis.add_geometry(voxel_grid)
        vis.run()
    print(volume_approximator)
    return volume_approximator


def analyze_data() -> tuple[float, np.ndarray, np.ndarray]:
    weights_path = "measured_weights.json"
    with open(weights_path, "r") as weights_file:
        weights = json.loads(weights_file.read())
    weights = np.array(weights)
    use_cache = False
    cache_path = "cached_data.json"
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, "r") as cache_file:
            cache = json.loads(cache_file.read())
            k = cache["k"]
            volumes = np.array(cache["volumes"])
            return k, volumes, weights
    measurement_volume = 0
    volumes = []
    for i in range(60):
        pc_dir = f"./pointclouds/segment_0/capture_{i}"
        measurement_volume += estimate_volume(pc_dir)
        if i % 10 == 9:
            volumes.append(measurement_volume)
            measurement_volume = 0
    for i in range(20):
        pc_dir = f"./pointclouds/segment_1/capture_{i}"
        measurement_volume += estimate_volume(pc_dir)
        if i % 10 == 9:
            volumes.append(measurement_volume)
            measurement_volume = 0

    volumes = np.array(volumes)
    # We will model the mass of cilantro as being purely proportional to our volume estimate
    # V * k = W
    k = ((volumes.T @ volumes) ** -1) * (volumes.T @ weights)
    with open(cache_path, "w") as cache_file:
        cache = {"k": k, "volumes": volumes.tolist()}
        cache_file.write(json.dumps(cache))

    return k, volumes, weights


if __name__ == "__main__":
    k, volumes, weights = analyze_data()

    average_weight = np.mean(weights)

    k = ((volumes.T @ volumes) ** -1) * (volumes.T @ weights)

    residuals = k * volumes - weights
    blind_residuals = average_weight - weights
    percent_error = np.abs(residuals / weights)
    blind_error = np.abs(blind_residuals / weights)
    avg_percent_error = np.mean(percent_error)
    avg_blind_error = np.mean(blind_error)
    plt.scatter(volumes, weights)
    min_x = np.min(volumes) * 0.9
    max_x = np.max(volumes) * 1.1
    plt.plot((min_x, max_x), (min_x * k, max_x * k), color="green")
    plt.xlabel("Volume Approximator")
    plt.ylabel("Measured Mass of Cilantro (grams)")
    title_font = {"family": "serif", "color": "blue", "size": 10}
    plt.title(
        f"Volume Approximator vs Cilantro Mass\nAverage Percent Error: {avg_percent_error * 100: .2f}%\nAverage Error Without Model: {avg_blind_error * 100: .2f}%",
        fontdict=title_font,
    )
    plt.savefig("Model.png")
    plt.show()
