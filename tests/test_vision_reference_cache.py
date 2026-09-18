import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from env.vision import FNAFVision


def make_vision(reference_dir: str, l_bbox: int = 4, r_bbox: int = 6) -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision.l_bbox = l_bbox
    vision.r_bbox = r_bbox
    vision.ref_left = None
    vision.ref_right = None
    vision.reference_dir = reference_dir
    return vision


def test_load_returns_false_when_no_cache_exists():
    with tempfile.TemporaryDirectory() as tmp:
        vision = make_vision(tmp)

        loaded = vision.load_reference_from_disk()

        assert loaded is False
        assert vision.ref_left is None
        assert vision.ref_right is None


def test_save_then_load_round_trips_the_reference_frames():
    with tempfile.TemporaryDirectory() as tmp:
        writer = make_vision(tmp)
        writer.ref_left = np.arange(16, dtype=np.float32).reshape(4, 4)
        writer.ref_right = np.arange(36, dtype=np.float32).reshape(6, 6)
        writer.save_reference_to_disk()

        reader = make_vision(tmp)
        loaded = reader.load_reference_from_disk()

        assert loaded is True
        assert np.array_equal(reader.ref_left, writer.ref_left)
        assert np.array_equal(reader.ref_right, writer.ref_right)


def test_load_rejects_cache_with_mismatched_bbox_size():
    with tempfile.TemporaryDirectory() as tmp:
        writer = make_vision(tmp, l_bbox=4, r_bbox=6)
        writer.ref_left = np.zeros((4, 4), dtype=np.float32)
        writer.ref_right = np.zeros((6, 6), dtype=np.float32)
        writer.save_reference_to_disk()

        reader = make_vision(tmp, l_bbox=10, r_bbox=6)
        loaded = reader.load_reference_from_disk()

        assert loaded is False
        assert reader.ref_left is None
        assert reader.ref_right is None


if __name__ == '__main__':
    test_load_returns_false_when_no_cache_exists()
    test_save_then_load_round_trips_the_reference_frames()
    test_load_rejects_cache_with_mismatched_bbox_size()
    print('ok')
