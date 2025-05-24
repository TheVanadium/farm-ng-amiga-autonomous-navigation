from fastapi import APIRouter, Depends
from multiprocessing import Queue

router = APIRouter()


# Dependency that injects the shared Queue into route functions
def get_message_queue():
    from main import queue

    return queue


@router.post("/save_point_cloud")
async def save_point_cloud(queue: Queue = Depends(get_message_queue)):
    # Send the message to the shared Queue
    queue.put("save_point_cloud")
    return {"status": "Point cloud saved"}
