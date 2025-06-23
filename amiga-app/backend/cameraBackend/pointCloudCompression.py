import open3d as o3d
import numpy as np
import DracoPy


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
