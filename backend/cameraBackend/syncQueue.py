# Modified code from
# https://github.com/luxonis/depthai-experiments/blob/master/gen2-multiple-devices/rgbd-pointcloud-fusion/host_sync.py

import numpy as np
from functools import reduce
from collections import deque
from typing import List


class SyncQueue:
    """
    A buffer for syncing frames by sequence number from depth and rgb streams.

    Args:
        streams (List[str]): List of stream names to track (['depth', 'rgb']).
        maxlen (int): Maximum number of frames to retain per stream queue (default: 50).

    Attributes:
        queues (Dict[str, deque]): Maps each stream name to its deque of message records.

    Methods:
        add(stream, frame):
            Add a new frame to the buffer for the given stream.
        get():
            Find the latest sequence number present in all stream buffers, remove any
            older frames, and return a dict mapping each stream name to its frame
            at that sequence. Returns None if there is no common sequence.

    Example:
        q = SyncQueue(['depth', 'rgb'], maxlen=50)
        q.add('depth', depth_frame)
        q.add('rgb', rgb_frame)
        synced = q.get()
        if synced:
            synced_depth_frame = synced['depth']
            synced_rgb_frame   = synced['rgb']
    """

    def __init__(self, streams: List[str], maxlen=50):
        self.queues = {stream: deque(maxlen=maxlen) for stream in streams}

    def add(self, stream: str, frame):
        self.queues[stream].append({"frame": frame, "seq": frame.getSequenceNum()})

    def get(self):
        seqs = [
            np.array([frame["seq"] for frame in frames])
            for frames in self.queues.values()
        ]

        matching_seqs = reduce(np.intersect1d, seqs)
        if len(matching_seqs) == 0:
            return None

        seq = np.max(matching_seqs)
        synced_frames = {
            stream: next(frame["frame"] for frame in frames if frame["seq"] == seq)
            for stream, frames in self.queues.items()
        }
        self.queues = {
            stream: deque(
                [frame for frame in frames if frame["seq"] > seq], maxlen=frames.maxlen
            )
            for stream, frames in self.queues.items()
        }
        return synced_frames
