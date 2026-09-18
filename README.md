# Fly-NAF

A whole-brain *Drosophila melanogaster* connectome simulation that plays Five Nights at Freddy's 1.

All 138,639 neurons of the FlyWire 783 connectome run as leaky integrate-and-fire units with their real synaptic weights. The screen is fed into the fly's visual clusters, and the mouse is driven by reading its descending neurons. Nothing in the loop decides anything on the fly's behalf.

## What the fly actually does

Three behaviours come out of the network, and each one is a different pathway.

**Slamming a door.** The hallway is captured while the light is on and compared against a reference of that same hallway empty. A difference above threshold drives the corresponding eye cluster at full rate, that excitation propagates through the real connectivity, and when DNp01, the Giant Fiber, crosses its own firing threshold the door closes. Measured on this machine, the neuron needs seven to nine engine frames of sustained input to answer, which is why the light is held for twelve.

**Checking a hallway.** The difference in membrane potential between the left and right eye populations is a slow spontaneous signal the network produces on its own, with a lag-1 autocorrelation of 0.97. It is accumulated to a bound together with what the last look revealed and a per-side habituation term, and whichever side wins gets looked at. There is one starvation guard, a clock that forces a look at a hallway left unwatched for thirty seconds, and every look it causes is counted separately in the session report so its share stays visible.

**Raising the monitor.** DNp09's own subthreshold membrane potential is accumulated the same way. A real spike raises the tablet outright, and the tablet comes down when that drive fades rather than when a timer expires.

Raising the tablet also drives the GABAergic inhibitor clusters at full rate, which silences both descending neurons. The fly is genuinely blind while it watches the cameras, exactly as it would be in the game.

## What this is not

There is no policy, no reward, no training and no learning. The connectome is fixed at what FlyWire measured. Every constant in `src/config.py` was fitted against measurements of the simulated network rather than chosen by feel, and the reasoning for each one is recorded in `docs/adr/`.

## Requirements

- Windows. The motor layer uses `ctypes` against the Win32 API and capture uses `mss`, so this does not run on Linux or macOS.
- Python 3.11 or newer, and [uv](https://docs.astral.sh/uv/).
- Five Nights at Freddy's 1, running windowed at 1280x720.
- A CUDA GPU is optional. On CPU the engine settles around 3.6 frames per second, which the timing constants account for.

## The connectome data is not in this repository

The simulation needs roughly 110 MB of FlyWire data that is deliberately not committed here. It comes from [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain), which is where the neural engine this project builds on lives, and from the FlyWire annotation supplement.

`src/config.py` resolves the data path relative to the parent of this repository, so the layout on disk has to look like this. The folder this repository sits in can have any name.

```
<parent folder>/
├── fly-brain/                  git clone https://github.com/eonsystemspbc/fly-brain
│   └── data/
│       ├── 2025_Connectivity_783.parquet     96 MB, signed synaptic weights
│       ├── 2025_Completeness_783.csv          3 MB, the neuron index
│       └── soma_coordinates_783.csv          10 MB, soma positions for the 3D panel
├── flywire_annotations/
│   └── supplemental_files/
│       └── Supplemental_file1_neuron_annotations.tsv   super_class per neuron
└── Fly-NAF/                    this repository
```

The annotations file is also found if you keep it under `fly-brain/data/flywire_annotations/` instead. Only the three data files and the annotation TSV are read. Everything else in the `fly-brain` clone is ignored.

## Setup

```bash
git clone https://github.com/eonsystemspbc/fly-brain.git
git clone <this repository> Fly-NAF
cd Fly-NAF
uv sync
```

Then place the FlyWire annotations beside the two clones as shown above.

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

Every run writes a report to `logs/session_telemetry_*.txt` covering who decided each look, what the eye measured against the threshold, how long the eye drove the cluster, and how much of the night the inhibitors were active.

## The live activity panel

A borderless, click-through overlay is pinned over the office showing all 138,639 somata in their real anatomical positions, lit as they fire. Brightness follows both the firing share and the on-screen point density, so the panel reads as an instrument rather than a white blob.

The full version, with per-region firing bars and counters, is served at `http://127.0.0.1:8770/` and can be opened in any browser at the same time.

## Documentation

`docs/adr/` holds the architecture decisions in Michael Nygard's format, each one carrying the measurement that drove it. `docs/experiments/` holds the investigations, including the failures. Reading ADR 0012 through 0016 in order gives the clearest account of how the current behaviour was arrived at.

## Licensing and credits

This project is licensed under the GNU General Public License version 3 or any later version, in `LICENSE`.

It has to be. Two files under `src/neural/` are adapted from `code/run_pytorch.py` in [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain). `models.py` carries the LIF neuron with alpha synapses, the delay buffer and the surrogate gradient, and `data_loader.py` carries the connectome loading. That repository is licensed under GPL version 2 or any later version, so this one inherits it, and version 3 is taken under the "or later" clause. The data files also come from its `data` folder.

Everything else here is original. An audit of all twenty source files against the upstream project found no meaningful overlap outside those two.

The connectome is FlyWire 783, from the [FlyWire consortium](https://flywire.ai/). None of that data is redistributed here. It stays subject to FlyWire's own terms and citation requirements, and anyone using this project has to obtain it from the sources listed above.

Five Nights at Freddy's is by Scott Cawthon and is not affiliated with this project.

| Versão | Descrição | Autor(es) | Data | Revisor(es) | Data de Revisão |
|---|---|---|---|---|---|
| 1.0 | README completo com dependência de dados, calibração e execução | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Correção da licença para GPL v3 após identificar obra derivada do fly-brain | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
