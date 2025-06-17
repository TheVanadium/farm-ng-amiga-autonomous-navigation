import os
import open3d as o3d
import numpy as np
from scipy.stats import pearsonr
from typing import TypeAlias
import matplotlib.pyplot as plt
import json

import volume


def analyze_data() -> tuple[float, np.ndarray, np.ndarray]:
    """
    Summary: Analyzes point cloud captures to create a linear model relating
             estimated volume to measured weight.

    Returns:
        k (float):
            Model parameter where estimated_volume * k = measured_weight.
        volumes (np.ndarray):
            1D array of cumulative estimated volumes for each batch of 10 captures.
        weights (np.ndarray):
            1D array of measured weights loaded from "measured_weights.json".
            Each entry corresponds to the same batch of captures in `volumes`.
    """

    weights_path = "measured_weights.json"
    with open(weights_path, "r") as weights_file:
        weights = json.loads(weights_file.read())
    weights = np.array(weights)

    use_cached_data = False

    cache_path = "cached_data.json"
    if use_cached_data and os.path.exists(cache_path):
        with open(cache_path, "r") as cache_file:
            cache = json.loads(cache_file.read())
            k = cache["k"]
            volumes = np.array(cache["volumes"])
            return k, volumes, weights

    measurement_volume = 0
    volumes = []
    for i in range(60):
        pc_dir = f"./pointclouds/segment_0/capture_{i}"
        measurement_volume += volume.height_volume_estimate(pc_dir)
        if i % 10 == 9:
            volumes.append(measurement_volume)
            measurement_volume = 0
    for i in range(20):
        pc_dir = f"./pointclouds/segment_1/capture_{i}"
        measurement_volume += volume.height_volume_estimate(pc_dir)
        if i % 10 == 9:
            volumes.append(measurement_volume)
            measurement_volume = 0

    volumes = np.array(volumes)
    # We will model the mass of cilantro as being purely proportional to our volume estimate
    # V * k = W
    # Solve least-squares
    k = float(((volumes.T @ volumes) ** -1) * (volumes.T @ weights))

    with open(cache_path, "w") as cache_file:
        cache = {"k": k, "volumes": volumes.tolist()}
        cache_file.write(json.dumps(cache))

    return k, volumes, weights


if __name__ == "__main__":
    k, volumes, weights = analyze_data()

    average_weight = np.mean(weights)

    k = ((volumes.T @ volumes) ** -1) * (volumes.T @ weights)

    residuals = k * volumes - weights
    blind_residuals = average_weight - weights
    percent_error = np.abs(residuals / weights)
    blind_error = np.abs(blind_residuals / weights)
    avg_percent_error = np.mean(percent_error)
    avg_blind_error = np.mean(blind_error)
    plt.scatter(volumes, weights)
    min_x = np.min(volumes) * 0.9
    max_x = np.max(volumes) * 1.1
    plt.plot((min_x, max_x), (min_x * k, max_x * k), color="green")
    plt.xlabel("Volume Approximator")
    plt.ylabel("Measured Mass of Cilantro (grams)")
    title_font = {"family": "serif", "color": "blue", "size": 10}
    plt.title(
        f"Volume Approximator vs Cilantro Mass\nAverage Percent Error: {avg_percent_error * 100: .2f}%\nAverage Error Without Model: {avg_blind_error * 100: .2f}%",
        fontdict=title_font,
    )
    plt.savefig("Model.png")
    plt.show()
