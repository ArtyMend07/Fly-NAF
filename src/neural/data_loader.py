import logging
import pandas as pd
import pickle
import torch
from pathlib import Path

_log = logging.getLogger(__name__)


def get_hash_tables(comp_path):
    df_comp = pd.read_csv(comp_path, index_col=0)
    flyid2i = {flyid: idx for idx, flyid in enumerate(df_comp.index)}
    i2flyid = {idx: flyid for flyid, idx in flyid2i.items()}
    return flyid2i, i2flyid


def load_connectome_weights(conn_path, comp_path, wt_dir, csr=True, device='cpu'):
    wt_dir = Path(wt_dir)
    wt_dir.mkdir(parents=True, exist_ok=True)
    coo_path = wt_dir / 'weight_coo.pkl'
    csr_path = wt_dir / 'weight_csr.pkl'

    flyid2i, _ = get_hash_tables(comp_path)
    num_neurons = len(flyid2i)

    weight_coo = None
    if coo_path.exists():
        with open(coo_path, 'rb') as f:
            weight_coo = pickle.load(f)
    else:
        _log.info('constructing COO weight matrix')
        data_conn = pd.read_parquet(conn_path)
        idx = [
            data_conn['Postsynaptic_Index'].to_list(),
            data_conn['Presynaptic_Index'].to_list(),
        ]
        val = data_conn['Excitatory x Connectivity'].to_list()
        weight_coo = torch.sparse_coo_tensor(
            idx, val, (num_neurons, num_neurons)
        ).to(torch.float32)
        with open(coo_path, 'wb') as f:
            pickle.dump(weight_coo, f)

    if csr:
        if csr_path.exists():
            with open(csr_path, 'rb') as f:
                weight_csr = pickle.load(f)
        else:
            _log.info('converting COO to CSR')
            weight_csr = weight_coo.to_sparse_csr()
            with open(csr_path, 'wb') as f:
                pickle.dump(weight_csr, f)
        return weight_csr.to(device)

    return weight_coo.to(device)