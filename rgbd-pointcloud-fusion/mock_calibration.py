import numpy as np
import cv2
import os
import math

# Mock intrinsic parameters (same for both cameras)
intrinsic_mat = np.array(
    [
        [2.82846289e03, 0.00000000e00, 1.92205481e03],
        [0.00000000e00, 2.82721777e03, 1.14587720e03],
        [0.00000000e00, 0.00000000e00, 1.00000000e00],
    ]
)

# Camera 1 - Assume it's at the origin of the world frame
rot_mat_1 = np.eye(3)  # Identity matrix (no rotation)
trans_vec_1 = np.array([0.0, 0.0, 0.0])  # Camera 1 is at the origin

# Camera 2 - Assume it's 50cm away along the x-axis
# rot_mat_2 = np.eye(3)  # Identity matrix (no rotation)
rot_mat_2 = np.array(
    [
        [1, 0, 0],  # Rotation by 180° around Y-axis to face Camera 1
        [0, -1, 0],
        [0, 0, -1],
    ],
    dtype=np.float32,
)
trans_vec_2 = np.array([0.0, 0.0, 0.908])  # Camera 2 is 50cm away in z direction

# Convert rotation matrices to rotation vectors (since cv2.solvePnP returns rotation vectors)
rot_vec_1, _ = cv2.Rodrigues(rot_mat_1)
rot_vec_2, _ = cv2.Rodrigues(rot_mat_2)

# Camera 1 extrinsics (world-to-camera transformation)
world_to_cam_1 = np.vstack(
    (np.hstack((rot_mat_1, trans_vec_1.reshape(-1, 1))), np.array([0, 0, 0, 1]))
)
cam_to_world_1 = np.linalg.inv(world_to_cam_1)

# Camera 2 extrinsics (world-to-camera transformation)
world_to_cam_2 = np.vstack(
    (np.hstack((rot_mat_2, trans_vec_2.reshape(-1, 1))), np.array([0, 0, 0, 1]))
)
cam_to_world_2 = np.linalg.inv(world_to_cam_2)

# Path where the extrinsic data will be saved
save_path = "calibration_data"
os.makedirs(save_path, exist_ok=True)

# Save extrinsic parameters for Camera 1
np.savez(
    os.path.join(save_path, "extrinsics_10.95.76.12.npz"),
    world_to_cam=world_to_cam_1,
    cam_to_world=cam_to_world_1,
    trans_vec=trans_vec_1,
    rot_vec=rot_vec_1,
)

# Save extrinsic parameters for Camera 2
np.savez(
    os.path.join(save_path, "extrinsics_10.95.76.13.npz"),
    world_to_cam=world_to_cam_2,
    cam_to_world=cam_to_world_2,
    trans_vec=trans_vec_2,
    rot_vec=rot_vec_2,
)

print("Extrinsic parameters saved to files.")
