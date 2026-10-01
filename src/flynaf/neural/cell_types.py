import logging
import os

import pandas as pd

from flynaf import config

_log = logging.getLogger(__name__)

COLUMNS = ['root_id', 'cell_type', 'side']


class CellTypeIndex:
    def __init__(self, table: pd.DataFrame):
        self._table = table[COLUMNS].dropna(subset=['cell_type'])

    @classmethod
    def load(cls, annotations: str = config.ANNOTATIONS_TSV,
             cache: str = config.CELL_TYPE_CACHE) -> 'CellTypeIndex':
        if _cache_is_current(cache, annotations):
            return cls(pd.read_parquet(cache))
        if not os.path.isfile(annotations):
            raise FileNotFoundError(
                'the FlyWire annotation table is missing at %s, run python -m flynaf.scripts.fetch_data'
                % annotations
            )
        _log.info('indexing FlyWire cell types from %s', os.path.basename(annotations))
        table = pd.read_csv(annotations, sep='\t', usecols=COLUMNS, dtype={'cell_type': str, 'side': str})
        table['root_id'] = table['root_id'].astype('int64')
        _write_cache(table, cache)
        return cls(table)

    def root_ids(self, cell_types, side: str | None = None) -> list:
        rows = self._table[self._table['cell_type'].isin(tuple(cell_types))]
        if side is not None:
            rows = rows[rows['side'] == side]
        return sorted(int(root_id) for root_id in rows['root_id'])

    def describe(self, root_id: int) -> str:
        rows = self._table[self._table['root_id'] == root_id]
        if rows.empty:
            return f'untyped {root_id}'
        row = rows.iloc[0]
        return f'{row["cell_type"]} ({row["side"]}) {root_id}'


def _cache_is_current(cache: str, annotations: str) -> bool:
    if not os.path.isfile(cache):
        return False
    if not os.path.isfile(annotations):
        return True
    return os.path.getmtime(cache) >= os.path.getmtime(annotations)


def _write_cache(table: pd.DataFrame, cache: str):
    try:
        table[COLUMNS].to_parquet(cache)
    except OSError as exc:
        _log.warning('cell type cache not written, it will be rebuilt next run: %s', exc)
