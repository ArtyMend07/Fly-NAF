import os

import pytest

from flynaf import config


def pytest_collection_modifyitems(items):
    if os.path.exists(config.CONNECTIVITY_PARQUET):
        return
    skip = pytest.mark.skip(reason=f'the FlyWire data is not at {config.DATA_DIR}')
    for item in items:
        if 'connectome' in item.keywords:
            item.add_marker(skip)
