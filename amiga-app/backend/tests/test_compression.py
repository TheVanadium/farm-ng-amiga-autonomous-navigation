from cameraBackend.pointCloudCompression import compress_pcd, decompress_drc
import open3d
import unittest

class TestCompression(unittest.TestCase):
    def test_loss_suite(self) -> None:
        def _test_loss(filename: str) -> None:
            pcd = open3d.io.read_point_cloud(filename)
            pcd2 = decompress_drc(compress_pcd(pcd))
            pcd = pcd.voxel_down_sample(voxel_size=0.1)
            pcd2 = pcd2.voxel_down_sample(voxel_size=0.1)
            assert abs(len(pcd.points) - len(pcd2.points)) <= 0.001 * len(pcd.points)
        _test_loss("tests/test_data/test_1.ply")
        _test_loss("tests/test_data/test_2.ply")

if __name__ == "__main__":
    unittest.main()
