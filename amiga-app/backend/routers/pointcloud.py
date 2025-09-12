import os

from fastapi import APIRouter, Request

from backend.config import CALIBRATION_DATA_DIR, POINTCLOUD_DATA_DIR

router = APIRouter()


@router.get("/pointcloud/save")
async def pointcloud_save(request: Request):
    """MEANT FOR INTERNAL TESTING USE ONLY"""
    """Save pointcloud to pointcloud_data_dir"""
    if not os.path.exists(POINTCLOUD_DATA_DIR):
        print("No calibration data directory found.")
        return {"message": "No point cloud directory found."}

    queue = request.state.camera_msg_queue
    queue.put({"action": "save_point_cloud"})

    return {"status": "Point cloud saved"}


@router.get("/pointcloud/align")
async def pointcloud_align(request: Request):
    """Create alignment config for cameras"""
    if not os.path.exists(CALIBRATION_DATA_DIR):
        print("No calibration data directory found.")
        return {"message": "No calibration data directory found."}

    queue = request.state.camera_msg_queue
    queue.put({"action": "align_point_clouds"})

    print("Attempting to set camera alignment (Not guranteed successful)")
    return {"status": "Attempting to set camera alignment (Not guranteed successful)"}


@router.get("/pointcloud/reset")
async def pointcloud_reset(request: Request):
    """Reset alignment of cameras"""
    if not os.path.exists(CALIBRATION_DATA_DIR):
        print("No calibration data directory found.")
        return {"message": "no calibration data directory found."}

    queue = request.state.camera_msg_queue
    queue.put({"action": "reset_alignment"})

    print("Resetting camera alignment")
    return {"status": "Camera alignment reset"}
