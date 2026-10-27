# ADR 0027: The Source Is The flynaf Package And pytest Runs It

## Status
Accepted.

## Context
Every module under `src/` was imported by its bare name, `import config`,
`from night.engine import ConnectomeEngine`. Nothing installed `src/`, so each
entry point put it on `sys.path` by hand. That was `run.py`, `replay.py`, every
script under `src/scripts/` and every one of the thirty-one test files. The
names it exposed at the top level were generic, `config`, `env`, `main`,
`replay`, and any installed distribution with the same name would have been
imported in their place depending on the order of the path.

The tests had no runner. Each file was a script whose `__main__` block called
its cases by name, and the list had drifted from the cases. `test_fetch_data.py`
had no `__main__` block at all, so running it as a script ran nothing, and
`test_motor_pan_settle.py` defined a case its block never called. Neither
failure was visible, because a script that runs no assertion prints the same
`ok`. pytest collected all 194 fast cases without any change to them, but it was
not a dependency, and neither was ruff, so nothing checked either on a push.

## Decision
The source moves to `src/flynaf/` and every import names the package,
`from flynaf import config`. `pyproject.toml` declares a hatchling build with
`src/flynaf` as its only package, so `uv sync` installs the project in editable
mode and no file touches `sys.path`. `run.py` stays at the root as the only
entry point, and the scripts and the replay run as modules,
`uv run python -m flynaf.scripts.fetch_data`.

pytest and ruff join the project as the `dev` dependency group. The two tests
that run the real engine on the FlyWire data, `test_inhibition.py` and
`test_pathways.py`, carry a `connectome` marker, and `tests/conftest.py` skips
that marker when the connectivity parquet is not in place. ruff runs the
pyflakes rules, the import sorter and the error subset of pycodestyle, which the
code passes as it stands.

A GitHub Actions workflow runs the lint and the tests on every push to `main`
and on every pull request. It runs on Windows, the platform the game runs on and
the one where PyTorch on PyPI is the CPU build. On Linux the same package pulls
the CUDA libraries, several gigabytes the runner would download and never use.

### Amendment, 2026-10-24: a Linux job on the CPU build of PyTorch

ADR 0017 made the replay and the panel run on Linux, and only the Windows runner checked them. The CUDA libraries are what kept Linux out, so the second job installs without them. `test-linux` runs on `ubuntu-24.04`, exports the locked versions with `uv export --locked`, drops the `cuda-`, `nvidia-` and `triton` lines and installs the rest with `uv pip install --torch-backend cpu`, which takes the same torch 2.13.0 from the PyTorch CPU index as `2.13.0+cpu`. Every other package stays at its locked version, and `uv pip check` found no conflict.

Replayed in WSL Ubuntu 22.04 with `DISPLAY` and `WAYLAND_DISPLAY` unset, as on a runner, the environment took 1.9 GB against 5.7 GB from `uv sync --locked`, of which 2.7 GB were the NVIDIA libraries and 0.7 GB triton. ruff passed, and pytest gave 489 passed and 15 skipped for the missing FlyWire data. The runner is pinned because `ubuntu-latest` moves to Ubuntu 26.04 in November 2026 ([runner-images #14748](https://github.com/actions/runner-images/issues/14748)).

The Windows job still installs with `uv sync --locked`, so the lock file is checked as a whole on the platform the game runs on, and the Linux job checks the code against the same versions.

### Amendment, 2026-10-27: SonarQube Cloud reads the Linux job

`test-linux` runs pytest with `pytest-cov`, writes `coverage.xml` and hands it to `SonarSource/sonarqube-scan-action` with the `SONAR_TOKEN` secret. The analysis covers `src/` and `run.py`, reads `tests/` as test code and leaves out `src/flynaf/env/assets/`, which holds the NeuroMechFly meshes and their licence. The settings are in [`sonar-project.properties`](../../sonar-project.properties), and `[tool.coverage.run]` in `pyproject.toml` writes the paths relative to the repository so the scanner can match them to the files it reads. The job clones the full history, since the scanner attributes each line through git blame to tell new code from old.

`models.py` and `data_loader.py`, adapted from `eonsystemspbc/fly-brain`, stay in the analysis. They are the engine and have been rewritten for the real-time loop, so leaving them out would hide code this project maintains. The quality gate judges the code each change adds, so what they carried over shows on the dashboard without failing a pull request.

Only one job sends the report, because the code is the same on both runners. The two `connectome` tests are skipped on the runner, so the engine they exercise reads as less covered on the dashboard than it is on a machine with the FlyWire data.

## Consequences
The FlyWire data cannot be redistributed, so the runner never holds it and the
two connectome tests are reported as skipped there. Everything they check is
still checked on a machine with the data, and the skip names the missing path.

`PROJECT_ROOT` in `config.py` climbs one directory more, since the file sits one
level deeper. The data still resolves to the folder that holds the repository,
and `logs/` and `tuning.toml` stay at the repository root.

`uv sync` installs pytest and ruff for anyone who runs the project, including
the one click setup, a few megabytes against the PyTorch download it already
makes.

The `__main__` blocks in the test files stay and still work, since the package
is installed, but pytest is the runner the README and the workflow use.

Earlier records name the old paths. ADR 0024 places the night under
`src/night/`, which is now `src/flynaf/night/`, and the experiments keep the
paths they were written with.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the move to the flynaf package, the pytest and ruff pipeline and the connectome marker | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
| 1.1 | Added a Linux job that installs the locked versions on the CPU build of PyTorch | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-24 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-24 |
| 1.2 | Sent the coverage of the Linux job to SonarQube Cloud | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-27 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-27 |
