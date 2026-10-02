import os
import tempfile

import numpy as np

from flynaf.env.vision import FNAFVision


def make_vision(reference_dir: str, l_bbox: int = 4, r_bbox: int = 6) -> FNAFVision:
    vision = FNAFVision.__new__(FNAFVision)
    vision.l_bbox = l_bbox
    vision.r_bbox = r_bbox
    vision.windows = {'left': (0, 0, 3, 5), 'right': (10, 10, 17, 12)}
    vision.banks = {(side, closed): [] for side in ('left', 'right') for closed in (False, True)}
    vision._distance_cache = {}
    vision.reference_dir = reference_dir
    return vision


def filled(writer: FNAFVision) -> FNAFVision:
    for (side, closed), bank in writer.banks.items():
        shape = writer._bank_shape(side, closed)
        base = 10.0 * closed
        bank.extend(np.full(shape, base + level, dtype=np.float32) for level in (1.0, 2.0, 3.0))
    return writer


def test_load_returns_false_when_no_cache_exists():
    with tempfile.TemporaryDirectory() as tmp:
        vision = make_vision(tmp)

        assert vision.load_reference_from_disk() is False
        assert all(not bank for bank in vision.banks.values())


def test_save_then_load_round_trips_every_bank():
    with tempfile.TemporaryDirectory() as tmp:
        writer = filled(make_vision(tmp))
        writer.save_reference_to_disk()

        reader = make_vision(tmp)

        assert reader.load_reference_from_disk() is True
        for key, bank in writer.banks.items():
            assert len(reader.banks[key]) == len(bank)
            for saved, loaded in zip(bank, reader.banks[key]):
                assert np.array_equal(saved, loaded)


def test_load_rejects_cache_with_mismatched_bbox_size():
    with tempfile.TemporaryDirectory() as tmp:
        filled(make_vision(tmp, l_bbox=4, r_bbox=6)).save_reference_to_disk()

        reader = make_vision(tmp, l_bbox=10, r_bbox=6)

        assert reader.load_reference_from_disk() is False
        assert all(not bank for bank in reader.banks.values())


def test_a_cache_from_before_the_banks_forces_a_live_calibration():
    with tempfile.TemporaryDirectory() as tmp:
        filled(make_vision(tmp)).save_reference_to_disk()
        os.remove(os.path.join(tmp, 'banks.json'))
        for name in ('ref_left.png', 'ref_right.png'):
            open(os.path.join(tmp, name), 'wb').close()

        assert make_vision(tmp).load_reference_from_disk() is False
