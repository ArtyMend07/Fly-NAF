import pandas as pd

def mine_top_50():
    print("Loading datasets...")
    conn = pd.read_parquet('../fly-brain/data/2025_Connectivity_783.parquet')
    anno = pd.read_csv('../flywire_annotations/supplemental_files/Supplemental_file1_neuron_annotations.tsv', sep='\t', low_memory=False)
    left_gf = 720575940622838154
    right_gf = 720575940632499757
    gaba_anno = anno[anno['top_nt'] == 'gaba']
    gaba_ids = set(gaba_anno['root_id'].unique())
    conn_left = conn[conn['Postsynaptic_ID'] == left_gf]
    conn_left_gaba = conn_left[conn_left['Presynaptic_ID'].isin(gaba_ids)]
    conn_right = conn[conn['Postsynaptic_ID'] == right_gf]
    conn_right_gaba = conn_right[conn_right['Presynaptic_ID'].isin(gaba_ids)]
    top_50_left = conn_left_gaba.sort_values(by='Connectivity', ascending=False).head(50)
    top_50_right = conn_right_gaba.sort_values(by='Connectivity', ascending=False).head(50)
    print("\n[LEFT GF TOP 50 GABAergic PRESYNAPSES]")
    left_ids = top_50_left['Presynaptic_ID'].tolist()
    print(f"Count: {len(left_ids)}")
    print(left_ids)
    print("\n[RIGHT GF TOP 50 GABAergic PRESYNAPSES]")
    right_ids = top_50_right['Presynaptic_ID'].tolist()
    print(f"Count: {len(right_ids)}")
    print(right_ids)

if __name__ == '__main__':
    mine_top_50()