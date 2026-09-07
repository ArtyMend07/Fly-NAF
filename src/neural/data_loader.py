import pandas as pd
import pickle
import torch
from pathlib import Path
import os

def get_hash_tables(comp_path):
    """Build flywire ID <-> tensor index mappings from completeness CSV."""
    df_comp = pd.read_csv(comp_path, index_col=0)
    flyid2i = {j: i for i, j in enumerate(df_comp.index)}
    i2flyid = {j: i for i, j in flyid2i.items()}
    return flyid2i, i2flyid

def load_connectome_weights(conn_path, comp_path, wt_dir, csr=True, device='cpu'):
    """
    Load or build sparse weight matrix from connectivity data.
    Caches weight_coo.pkl / weight_csr.pkl in wt_dir for reuse.
    """
    wt_dir = Path(wt_dir)
    wt_dir.mkdir(parents=True, exist_ok=True)
    coo_path = wt_dir / 'weight_coo.pkl'
    csr_path = wt_dir / 'weight_csr.pkl'

    data_name = pd.read_csv(comp_path)
    num_neurons = data_name.shape[0]

    weight_coo = None
    if coo_path.exists():
        with open(coo_path, 'rb') as f:
            weight_coo = pickle.load(f)
    else:
        print('Weights not found, constructing COO weight matrix...')
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
            print('CSR weights not found, converting from COO...')
            weight_csr = weight_coo.to_sparse_csr()
            with open(csr_path, 'wb') as f:
                pickle.dump(weight_csr, f)
        return weight_csr.to(device)
    else:
        return weight_coo.to(device)