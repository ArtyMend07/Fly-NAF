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
