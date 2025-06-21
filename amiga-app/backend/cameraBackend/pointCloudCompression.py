import open3d as o3d
import numpy as np
import DracoPy

def compress_pcd(pcd: o3d.geometry.PointCloud) -> bytes:
    points = np.asarray(pcd.points, dtype=np.float32)
    colors = (np.asarray(pcd.colors) * 255).astype(np.uint8)
    return DracoPy.encode(points, colors=colors)


def decompress_drc(draco_binary: bytes) -> o3d.geometry.PointCloud:
    decoded_drc = DracoPy.decode(draco_binary)
    if not hasattr(decoded_drc, 'points'):
        raise ValueError("Input missing points")
    if not hasattr(decoded_drc, 'colors'):
        raise ValueError("Input missing colors")
    
    decompressed_points = o3d.utility.Vector3dVector(np.asarray(decoded_drc.points))
    decompressed_colors = o3d.utility.Vector3dVector(np.asarray(decoded_drc.colors)/255)

    decompressed_pcd = o3d.geometry.PointCloud(decompressed_points)
    decompressed_pcd.colors = decompressed_colors
    return decompressed_pcd
