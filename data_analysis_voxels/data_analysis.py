from cameraBackend.pointCloudCompression import decompress_drc # PYTHONPATH="amiga-app/backend"
from sklearn.linear_model import LinearRegression
import numpy as np
import open3d as o3d
from open3d.visualization import draw

# can't combine because cameras aren't aligned or something
# def combine_pcds(pcds: list[o3d.geometry.PointCloud]) -> o3d.geometry.PointCloud:
#     """Puts all points in given point clouds into one point cloud"""
#     combined_pcd = o3d.geometry.PointCloud()
#     for pcd in pcds:
#         combined_pcd.points.extend(pcd.points)
#         combined_pcd.colors.extend(pcd.colors)
#     return combined_pcd

def voxel_count(pcd: o3d.geometry.PointCloud, voxel_size: int = 1) -> int:
    return len(pcd.voxel_down_sample(voxel_size).points)

# get data
point_clouds: list[list[o3d.geometry.PointCloud]] = [[None] * 3 for _ in range(4)]
for i in range(4):
    for j in range(3):
        file_path = f"data/capture_{i+1}/10.95.76.1{j+1}.drc"
        with open(file_path, "rb") as f:
            point_clouds[i][j] = decompress_drc(f.read())
            # draw(
            #     point_clouds[i][j],
            #     title=f"Capture {i+1} Camera {j+1}",
            #     width=800,
            #     height=600,
            # )
    # point_clouds[i][3] = combine_pcds(point_clouds[i][:3])

# count voxels
voxel_counts = np.array([[len(pcd.points) for pcd in row] for row in point_clouds])
print(voxel_counts)

# get weights
with open("data/weights.txt", "r") as f:
    weights = np.array([int(line.strip()) for line in f.readlines()])

# fit linear regression
model = LinearRegression()
model.fit(voxel_counts, weights)
print("Coefficients:", model.coef_)
print("Intercept:", model.intercept_)
print("R^2 score:", model.score(voxel_counts, weights))
