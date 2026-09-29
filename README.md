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

- Windows, or Linux on an X11 session. Wayland cannot work, because screen capture, synthetic pointer input and a click-through window are all unavailable to a Wayland client. On Linux the game itself would run under Wine or Proton, but that path has only been exercised against a live X11 server without the game present, as ADR 0017 describes; a full night through Wine or Proton has not been run yet.
- Nothing but Python is needed for the two inspection paths below. Those run on macOS too.
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
│       ├── soma_coordinates_783.csv          15 MB, FlyWire Codex positions for the 3D panel
│       └── brain_mesh_flywire.ply             1 MB, brain outline for the 3D panel
├── flywire_annotations/        git clone https://github.com/flyconnectome/flywire_annotations
│   └── supplemental_files/
│       └── Supplemental_file1_neuron_annotations.tsv   31 MB, super_class per neuron
└── Fly-NAF/                    this repository
```

Only two of those files ship inside the `fly-brain` clone. `soma_coordinates_783.csv` is the FlyWire Codex release at `https://storage.googleapis.com/flywire-data/codex/data/fafb/783/coordinates.csv.gz`, decompressed and renamed, and the panel looks each neuron up in it by root id. A file in any other layout is replaced by `fetch_data.py`, because an earlier copy with the right ids and unrelated coordinates drew every neuron in the place of another one (experiment 12). `brain_mesh_flywire.ply` is the FlyWire brain surface published by navis-flybrains, fetched at a fixed commit and checked against its hash. Only the panel reads either of them, and the panel draws the neurons without an outline when the mesh is missing.

The annotations file is also found if you keep it under `fly-brain/data/flywire_annotations/` instead. Only the three data files and the annotation TSV are read. Everything else in the `fly-brain` clone is ignored.

## Then why are those files not in the repository?

Three reasons, and the first one settles it on its own.

FlyWire releases the connectome under CC BY-NC 4.0, which allows sharing with attribution but forbids commercial use. This project is GPL v3, and the GPL does not allow extra restrictions to be layered on top of it. Shipping the data here would put two incompatible licences in the same repository.

The `flywire_annotations` supplement carries no licence file at all, so redistributing that one would be worse still.

And `2025_Connectivity_783.parquet` is 97 MB against a hard limit of 100 MB per file on GitHub, so it would stop working on whichever release grows it past that line.

## Setup

```bash
git clone <this repository> Fly-NAF
cd Fly-NAF
uv sync
uv run python src/scripts/fetch_data.py
```

`fetch_data.py` prints the licences first, then clones the two repositories and
downloads `soma_coordinates_783.csv` and `brain_mesh_flywire.ply` into place. It fetches, it never
redistributes. `--check` reports what is present without downloading anything.

## Three ways in

Not everything here needs the game, and two of the three need no purchase at all.

**Check what is in the loop.** Needs the data and nothing else, on any operating
system.

```bash
uv run python run.py --verify
```

**Replay a recorded night through the brain.** Needs the data and a trace. No
game, no Windows, no screen. This is the honest way to confirm that a hallway
reading reaches DNp01 and closes a door.

```bash
uv run python run.py --replay
```

**Play a night.** Needs the game installed. The launcher opens it for you.

```bash
uv run python run.py
```

## Calibration

The screen targets follow the game window. Once the game is the window in
front, its client rectangle is measured and every coordinate in `src/config.py`
is treated as a position inside a 1280x720 reference layout and scaled onto it.
A window of a different size or in a different corner works without any
measuring. The game draws at 1280x720 whatever the display, and in fullscreen
it switches the display to that mode, so the reference layout and the screen
are the same thing there.

A minimised window is never measured, because Windows reports it as a small
rectangle far off screen. If the game is not in front when the night starts,
the coordinates are used exactly as written, which assumes a 1280x720 window at
the top left. The scripts below stay for that case, and for inspecting what
each region actually reads.

- `src/scripts/select_roi.py` takes a screenshot and lets you drag the two hallway capture boxes.
- `src/scripts/vision_calibrator.py` writes the measured values into `logs/`.
- `src/scripts/debug_vision.py` and `src/scripts/debug_camera.py` show live what each capture region is reading.
- `src/scripts/debug_reflex.py` shows the live contrast of both hallways against the threshold, and says whether a door would slam. Run it with a light held on, because a reading taken with the light off means nothing.

The eye references are captured once and cached in `logs/vision_reference/`,
alongside a fingerprint of the layout they were taken on. They are re-measured
automatically whenever the capture size, the capture point or the game window
changes, so a stale reference cannot be loaded silently.

## Changing how the fly behaves

The first run writes `tuning.toml` next to this file. It exposes seven settings,
each with the range a measurement supports, and it explains what each one does.
A value outside its range is clamped and the clamp is reported when the run
starts.

`arousal_multiplier` and `subliminal_noise_hz` stop where the sweep in ADR 0013
stopped. Ten is not a bold setting for arousal, it is the documented seizure.
The LIF constants and the FlyWire root ids are deliberately not reachable from
that file, because they are the claim rather than a setting. Delete the file to
go back to the defaults.

## Running a night

```bash
uv run python run.py
```

On Windows, double-clicking `Fly-NAF.bat` does the same, and `src/main.py` run
directly goes through the same path.

A launcher window opens with the two choices the game's menu offers, New Game
and Continue, and the night the save file is on. Picking one opens the game
through Steam, loads the brain, brings the game to the front and clicks that
option in the menu, so the night starts only once the brain is ready to play
it. A copy outside Steam is opened through `GameLauncher.executable` in
`src/config.py`. `--new` and `--continue` do the same without the window.

The menu clicks need two points measured once, `new_game_x`, `new_game_y`,
`continue_x` and `continue_y` in `GameLauncher`, in the same 1280x720 layout as
every other target. Until they are set, the launcher still opens the game and
brings it to the front, and the menu choice is left to you during the ten
seconds before the fly starts. The launcher never clicks a game it did not open
itself, because a game that was already running may be in the middle of a
night.

`--manual`, or the button at the bottom of the launcher, keeps the old flow. The
brain loads, the activity panel opens over the office, and a ten second
countdown starts. Go to the game and start a night inside that window. In every
case the fly then centres the view, captures its office reference and takes
over.

The first run after a calibration change performs live calibration, which turns each hallway light on in turn to record what an empty hallway looks like. **Both hallways have to be empty at that moment**, otherwise an animatronic gets recorded as the normal state and the fly stays blind for the rest of the night.

Every run writes a report to `logs/session_telemetry_*.txt` covering who decided each look, what the eye measured against the threshold, how long the eye drove the cluster, and how much of the night the inhibitors were active. One real report is kept at `docs/example-session-report.txt` so the format and the numbers can be read without running anything.

## The live activity panel

When the game runs in a window, the panel sits beside it at the height of the game, so one screen recording holds both. It shows all 138,639 somata in their real anatomical positions, lit as they fire, between two readouts of the same clock. Above the brain is what the fly receives, the patch of each hallway, how far it differs from the reference against the threshold, and whether that input is driving the eye cluster, greyed out while the light on that side is off. Below it is a 20 second timeline of the input, the eye cluster spikes, DNp01, the door and the tablet.

When DNp01 fires, the panel traces the spike backwards through the synapses whose presynaptic neuron fired just before it, and replays that trace over the real neurons 150 times slower than simulated time, with a caption giving its depth in frames and simulated milliseconds and whether it reaches the eye cluster. Nothing on the panel is triggered by the game. Each element is a variable the simulation already holds, and ADR 0022 explains what the trace does and does not show.

A game that fills the screen gets the smaller overlay pinned over the office instead, and the full page is always served at `http://127.0.0.1:8770/` for any browser.

## Verifying what is in the loop

The claim at the top of this file is checkable without installing the game.

```bash
uv run python src/scripts/verify_connectome.py
```

It prints the neuron count, the edge count, the coverage against the FlyWire annotations, the super class of every neuron left out, the dimensions of the matrix handed to the engine, how many rows were dropped before it, and the gain in force. It needs the connectome data in place and nothing else.

Every run also writes a trace to `logs/traces/`, one line per engine frame,
carrying the input the eyes produced and what the descending neurons did with
it. `uv run python src/replay.py <trace>` feeds that input back through a real
engine and reports whether the giant fiber answers, how long it took and whether
it stayed quiet on idle frames.

Replay does not reproduce a night frame for frame, and it is not meant to. The
Poisson generator and the background noise are unseeded on purpose, because the
fly behaves stochastically. What holds across runs is the shape, and the report
says which parts of it count as a failure. Set `FLYNAF_RECORD=0` to turn
recording off.

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

For the parts of this README that are new, ADR 0017 covers the platform layer
and why Wayland is out, ADR 0018 covers the move from absolute screen pixels to
targets that follow the game window, ADR 0019 covers the trace format and what
replay does and does not prove, ADR 0020 covers which settings are exposed
for tuning and where their ranges come from, ADR 0021 covers the launcher
and why the game is measured only once it is in front, and ADR 0022 covers the
panel and the rule that only simulation variables drive it.

## Licensing and credits

This project is licensed under the GNU General Public License version 3 or any later version, in `LICENSE`.

It has to be. Two files under `src/neural/` are adapted from `code/run_pytorch.py` in [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain). `models.py` carries the LIF neuron with alpha synapses, the delay buffer and the surrogate gradient, and `data_loader.py` carries the connectome loading. That repository is licensed under GPL version 2 or any later version, so this one inherits it, and version 3 is taken under the "or later" clause. The data files also come from its `data` folder.

Everything else here is original. An audit of all twenty source files against the upstream project found no meaningful overlap outside those two.

The fly in the launcher is the NeuroMechFly body model from [NeLy-EPFL/flygym](https://github.com/NeLy-EPFL/flygym), built from a micro-CT scan of an adult female fly and licensed under Apache 2.0, which the GPL v3 can include. `src/scripts/build_fly_model.py` downloads its simplified meshes at a fixed commit, poses them in the neutral stance and writes `src/env/assets/neuromechfly.bin.gz`, and the Apache licence travels with it as `src/env/assets/LICENSE-neuromechfly.txt`. The brain outline in the panel comes from [navis-flybrains](https://github.com/navis-org/navis-flybrains), GPL v3, made from the FAFB tissue mask, and is downloaded rather than committed. `src/env/assets/CHANGES-neuromechfly.txt` states what was changed from the original meshes, as the Apache licence asks of a derived file. The model is Lobato-Rios et al., *NeuroMechFly, a neuromechanical model of adult Drosophila melanogaster*, Nature Methods 2022, and Wang-Chen et al., *NeuroMechFly v2*, Nature Methods 2024, and both ask to be cited by anyone using the model, which this note does on their behalf.

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
| 1.7 | Added the Linux path, the replay demo, automatic calibration and the tuning file | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-24 |
| 1.8 | Replaced the manual start with the launcher and documented the menu points | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
| 1.9 | Described the panel beside the game, its stimulus and timeline bands and the cascade replay | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
| 1.10 | Documented the Codex soma file, the brain outline and the NeuroMechFly model with their licences | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 |
| 1.11 | Added the required notice of changes to the NeuroMechFly assets and its citation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 |
| 1.12 | Clarified that the Wine or Proton path has not been run end to end yet | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-29 |
