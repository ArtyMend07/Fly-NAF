import numpy as np


def frame_distance(frame: np.ndarray, reference: np.ndarray) -> float:
    return float(np.mean((frame - reference) ** 2))


def nearest(frame: np.ndarray, bank: list) -> tuple:
    distances = [frame_distance(frame, reference) for reference in bank]
    index = int(np.argmin(distances))
    return distances[index], bank[index]


def add_if_new(bank: list, frame: np.ndarray, tolerance: float) -> bool:
    if bank and nearest(frame, bank)[0] <= tolerance:
        return False
    bank.append(frame)
    return True


def median_index(values: list) -> int:
    return int(np.argsort(values)[len(values) // 2])
