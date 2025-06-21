import open3d as o3d
from open3d.web_visualizer import draw
import numpy as np
import DracoPy

pcd = o3d.io.read_point_cloud("combined.ply")
points = np.asarray(pcd.points, dtype=np.float32)
colors = (np.asarray(pcd.colors) * 255).astype(np.uint8)
print(colors)
print(pcd)
draw(pcd)

binary = DracoPy.encode(points, colors=colors)

with open("combined.drc", "wb") as f:
    f.write(binary)

with open("combined.drc", "rb") as f:
    decompressed_read = DracoPy.decode(f.read())

decompressed_points = o3d.utility.Vector3dVector(np.asarray(decompressed_read.points))

decompressed_colors = o3d.utility.Vector3dVector(np.asarray(decompressed_read.colors)/255)
decompressed_pcd = o3d.geometry.PointCloud(decompressed_points)
decompressed_pcd.colors = decompressed_colors

draw(decompressed_pcd)
