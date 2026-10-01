# ADR 0025: Populations Are Resolved by FlyWire Cell Type

## Status
Accepted. Extends ADR 0005, whose rule that every pathway is a real FlyWire connection stands.

## Context
Every population the engine drove or read was a list of root ids pasted into `config.py`. The eye clusters were fifty LPLC2 per side, chosen in experiment 03, out of the 108 and 102 that FlyWire 783 annotates. LC4, the other looming projection onto the Giant Fiber, was absent even though it contributes 374 and 431 synapses to DNp01 against 458 and 622 from LPLC2. Von Reyn et al. 2017 and Ache et al. 2019 show that the Giant Fiber sums the two, LC4 encoding angular velocity and LPLC2 angular size.

Pasted ids also hide intent. A list of fifty integers cannot say that it means "LPLC2 on the left", so nothing flags it when half the type is missing, and adding a population for a new behaviour means another pasted list.

## Decision
Populations are declared by role and cell type in `CellPopulations`, and `neural/cell_types.py` resolves them against the Schlegel et al. 2024 annotation table, split by the `side` column. The resolved table is cached next to the connectome as `cell_types_783.parquet` and rebuilt whenever the annotation file is newer.

| Role | Cell types | Neurons, left and right |
|---|---|---|
| Hallway eye | LPLC2, LC4 | 162, 152 |
| Figure | LC9, LC31a | 105, 109 |
| Loom size | LPLC2 | 108, 102 |
| Loom speed | LC4 | 54, 50 |
| Door reflex | DNp01 | 1, 1 |
| Looming escape | DNp04 | 1, 1 |
| Exploration | DNp09 | 2 |

`night/neurons.py` turns the roles into a `NeuronMap` of engine indices, and the engine builds its rates from that map rather than from named fields. The GABAergic inhibitor lists stay as root ids, because they are the output of a mining script over synapse counts, not a cell type.

## Consequences
- The hallway eye now carries all of LPLC2 and all of LC4. Measured on the engine, the Giant Fiber still answers at frame 3, and DNp02 and DNp11 are recruited alongside it, as the looming literature predicts.
- The annotation table becomes a runtime dependency. It was already a required download in `fetch_data.py`, and the first run pays a few seconds to build the cache.
- A population that resolves to nothing raises at start-up, so a renamed cell type in a future release fails loudly instead of leaving a silent cluster.
- The search drive normalises its evidence by the larger of the two eye populations, since the sides are no longer the same size.
- `find_motor_pathway.py`, broken since the helpers it imported were removed, now searches between any two cell types.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Populations declared by cell type and resolved from the FlyWire annotations, LC4 added to the eye | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 |
