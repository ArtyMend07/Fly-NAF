import numpy as np

from flynaf.env.tablet_feed import cell_means, prepare


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


def changed_share(frame: np.ndarray, reference: np.ndarray, scale: int, cell: int, noise: float) -> float:
    size = (max(1, frame.shape[1] // scale), max(1, frame.shape[0] // scale))
    difference = (prepare(reference, size) - prepare(frame, size)) ** 2
    means, covered = cell_means(difference, np.ones(difference.shape, bool), cell)
    if not covered.any():
        return 0.0
    return float((means[covered] > noise).mean())
