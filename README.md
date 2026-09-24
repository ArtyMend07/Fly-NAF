# Fly-NAF

A whole-brain *Drosophila melanogaster* connectome simulation that plays Five Nights at Freddy's 1.

138,639 of the 139,255 proofread neurons in the FlyWire 783 connectome run as leaky integrate-and-fire units, wired by the measured synaptic weights. That is 99.56% of the brain, and the ones left out are almost all sensory afferents rather than interneurons. Nothing else is subset. The screen is fed into the fly's visual clusters, and the mouse is driven by reading its descending neurons.

## Best run so far

The fly reached 4 AM on night 2. The run is recorded at
https://www.youtube.com/watch?v=4UNPlA-YJtw.

## What the fly actually does

Three behaviours come out of the network, and each one is a different pathway.

**Slamming a door.** The hallway is captured while the light is on and compared against a reference of that same hallway empty. A difference above threshold drives the corresponding eye cluster at full rate, that excitation propagates through the real connectivity, and when DNp01, the Giant Fiber, crosses its own firing threshold the door closes. Measured on this machine, the neuron needs seven to nine engine frames of sustained input to answer, which is why the light is held for twelve.

**Checking a hallway.** The difference in membrane potential between the left and right eye populations is a slow spontaneous signal the network produces on its own, with a lag-1 autocorrelation of 0.97. It is accumulated to a bound together with what the last look revealed and a per-side habituation term, and whichever side wins gets looked at. There is one starvation guard, a clock that forces a look at a hallway left unwatched for thirty seconds, and every look it causes is counted separately in the session report so its share stays visible.

**Raising the monitor.** DNp09's own subthreshold membrane potential is accumulated the same way. A real spike raises the tablet outright, and the tablet comes down when that drive fades rather than when a timer expires.

Raising the tablet also drives the GABAergic inhibitor clusters at full rate, which silences both descending neurons. The fly is genuinely blind while it watches the cameras, exactly as it would be in the game.

## What this is not

There is no policy, no reward, no training and no learning whatsoever. The connectome is fixed at what FlyWire measured. Every constant in `src/config.py` was fitted against measurements of the simulated network rather than chosen by feel.

One thing is not a measurement. `arousal_multiplier` in `src/config.py` multiplies every weight in the matrix by 3, standing in for the neuromodulatory tone a brain in a body would have. The sign and the topology are untouched, the gain is uniform, and no edge is treated differently from any other, but the magnitude is not what FlyWire recorded.

FlyWire maps the brain and stops at the neck. There is no ventral nerve cord here, so the descending neurons are read where they leave the brain rather than driving a simulated body.

## Requirements

- Windows. The motor layer uses `ctypes` against the Win32 API and capture uses `mss`, so this does not run on Linux or macOS.
- Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/).
- Five Nights at Freddy's 1, running windowed at 1280x720.
- A CUDA GPU is optional. On CPU the engine settles around 3.6 frames per second, which the timing constants account for.

## The connectome data is not in this repository

The simulation needs roughly 140 MB of FlyWire data that is deliberately not committed here. It comes from [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain), which is where the neural engine this project builds on lives, and from the FlyWire annotation supplement.

`src/config.py` resolves the data path relative to the parent of this repository, so the layout on disk has to look like this. The folder this repository sits in can have any name.

```
<parent folder>/
├── fly-brain/                  git clone https://github.com/eonsystemspbc/fly-brain
│   └── data/
│       ├── 2025_Connectivity_783.parquet     97 MB, signed synaptic weights
│       ├── 2025_Completeness_783.csv          4 MB, the neuron index
│       └── soma_coordinates_783.csv          11 MB, soma positions for the 3D panel
├── flywire_annotations/        git clone https://github.com/flyconnectome/flywire_annotations
│   └── supplemental_files/
│       └── Supplemental_file1_neuron_annotations.tsv   31 MB, super_class per neuron
└── Fly-NAF/                    this repository
```

Only two of those files ship inside the `fly-brain` clone. `soma_coordinates_783.csv` is not one of them, and has to be fetched separately from the FlyWire Codex release at `https://storage.googleapis.com/flywire-data/codex/data/fafb/783/coordinates.csv.gz`, then decompressed and renamed. The 3D panel is the only thing that reads it.

The annotations file is also found if you keep it under `fly-brain/data/flywire_annotations/` instead. Only the three data files and the annotation TSV are read. Everything else in the `fly-brain` clone is ignored.

## Then why are those files not in the repository?

Three reasons, and the first one settles it on its own.

FlyWire releases the connectome under CC BY-NC 4.0, which allows sharing with attribution but forbids commercial use. This project is GPL v3, and the GPL does not allow extra restrictions to be layered on top of it. Shipping the data here would put two incompatible licences in the same repository.

The `flywire_annotations` supplement carries no licence file at all, so redistributing that one would be worse still.

And `2025_Connectivity_783.parquet` is 97 MB against a hard limit of 100 MB per file on GitHub, so it would stop working on whichever release grows it past that line.

## Setup

```bash
git clone https://github.com/eonsystemspbc/fly-brain.git
git clone https://github.com/flyconnectome/flywire_annotations.git
git clone <this repository> Fly-NAF
cd Fly-NAF
uv sync
```

Then fetch `soma_coordinates_783.csv` into `fly-brain/data/` as described above.

## Calibration

Every screen coordinate in `src/config.py` is measured for one specific layout, a 1280x720 game window at the top-left of the display. On any other resolution or window position the fly will click on nothing and see nothing, so these have to be redone.

- `src/scripts/select_roi.py` takes a screenshot and lets you drag the two hallway capture boxes.
- `src/scripts/vision_calibrator.py` writes the measured values into `logs/`.
- `src/scripts/debug_vision.py` and `src/scripts/debug_camera.py` show live what each capture region is reading.
- `src/scripts/debug_reflex.py` shows the live contrast of both hallways against the threshold, and says whether a door would slam. Run it with a light held on, because a reading taken with the light off means nothing.

The eye references are captured once and cached in `logs/vision_reference/`. They are re-measured automatically whenever the configured capture size changes.

## Running a night

```bash
uv run python src/main.py
```

Leave the terminal focused. The brain loads, the activity panel opens over the office, and a ten second countdown starts. Go to the game and start a night inside that window. The fly then centres the view, captures its office reference and takes over.

The first run after a calibration change performs live calibration, which turns each hallway light on in turn to record what an empty hallway looks like. **Both hallways have to be empty at that moment**, otherwise an animatronic gets recorded as the normal state and the fly stays blind for the rest of the night.

Every run writes a report to `logs/session_telemetry_*.txt` covering who decided each look, what the eye measured against the threshold, how long the eye drove the cluster, and how much of the night the inhibitors were active. One real report is kept at `docs/example-session-report.txt` so the format and the numbers can be read without running anything.

## The live activity panel

A borderless, click-through overlay is pinned over the office showing all 138,639 somata in their real anatomical positions, lit as they fire. Brightness follows both the firing share and the on-screen point density, so the panel reads as an instrument rather than a white blob.

The full version, with per-region firing bars and counters, is served at `http://127.0.0.1:8770/` and can be opened in any browser at the same time.

## Verifying what is in the loop

The claim at the top of this file is checkable without installing the game.

```bash
uv run python src/scripts/verify_connectome.py
```

It prints the neuron count, the edge count, the coverage against the FlyWire annotations, the super class of every neuron left out, the dimensions of the matrix handed to the engine, how many rows were dropped before it, and the gain in force. It needs the connectome data in place and nothing else.

## Tests

There is no test framework dependency. Every file under `tests/` is a script
that runs its own cases and prints `ok` when they all hold.

```bash
uv run python tests/test_hallway_detection.py
```

Most of them stub out the vision and motor layers and finish in under a second.
Four of them, `test_inhibition.py`, `test_pathways.py`, `test_engine_rate_reset.py`
and `test_search_loop_wiring.py`, load the real connectome, so they need the
FlyWire data in place and take a few minutes each.

## Documentation

`docs/adr/` holds the architecture decisions in Michael Nygard's format, each one carrying the measurement that drove it, and `docs/experiments/` holds the investigations, including the failures. ADR 0006 explains why inhibition is done with GABAergic clusters rather than a boolean flag, and experiment 03 covers the LPLC2 to DNp01 escape pathway the door reflex rides on.

## Licensing and credits

This project is licensed under the GNU General Public License version 3 or any later version, in `LICENSE`.

It has to be. Two files under `src/neural/` are adapted from `code/run_pytorch.py` in [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain). `models.py` carries the LIF neuron with alpha synapses, the delay buffer and the surrogate gradient, and `data_loader.py` carries the connectome loading. That repository is licensed under GPL version 2 or any later version, so this one inherits it, and version 3 is taken under the "or later" clause. The data files also come from its `data` folder.

Everything else here is original. An audit of all twenty source files against the upstream project found no meaningful overlap outside those two.

The connectome is FlyWire 783, from the [FlyWire consortium](https://flywire.ai/). None of that data is redistributed here. It is released under CC BY-NC 4.0 and stays subject to FlyWire's own terms and citation requirements, so anyone using this project has to obtain it from the sources listed above.

Five Nights at Freddy's is by Scott Cawthon and is not affiliated with this project.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Full README covering the data dependency, calibration and running | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Licence corrected to GPL v3 after identifying code derived from fly-brain | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.2 | Documented how the test scripts are run and what they depend on | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
| 1.3 | Recorded the best run reached so far | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-19 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-19 |
| 1.4 | Corrected where each data file comes from | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-20 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-20 |
| 1.5 | Explained why the connectome data cannot be committed here | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-20 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-20 |
| 1.6 | Stated the neuron coverage exactly, disclosed the global gain and added the verification script | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 |
