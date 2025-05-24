import open3d as o3d

pcd = o3d.io.read_point_cloud("./sample_data/combined.ply")

print(f"Loaded point cloud: {len(pcd.points)} points")

pcd = pcd.remove_statistical_outlier(nb_neighbors=50, std_ratio=0.5)[0]
# pcd, _ = pcd.remove_radius_outlier( nb_points=16, radius=2.0) # radius in mm

o3d.visualization.draw_geometries(
    [pcd],
    window_name="Loaded PLY Point Cloud",
    width=800,
    height=600,
    point_show_normal=False,
)
