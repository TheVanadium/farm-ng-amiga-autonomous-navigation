from multiprocessing import Process, Queue
import multiprocessing
from cameraBackend.oakManager import startCameras


def main():
    while True:
        user_input = input("a or s: ").lower()

        if user_input == "a":
            queue.put("align_point_clouds")
        elif user_input == "s":
            queue.put("save_point_cloud")


multiprocessing.set_start_method("fork")
queue = Queue()
oakManager = Process(target=startCameras, args=(queue,))
oakManager.start()
print(f"camera PID: {oakManager.pid}")
main()
