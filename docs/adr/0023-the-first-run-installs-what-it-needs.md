# ADR 0023: The First Run Installs What It Needs

## Status
Accepted.

## Context
Playing a night needed a sequence that only a developer would carry out. Install
uv, clone or download the repository, run a separate script to fetch the data,
and only then start the program. The script itself required git, because it
cloned two repositories, and the program answered missing data by telling the
operator to run the script by hand. Someone who owns the game and nothing else
had no path through it.

## Decision
`Fly-NAF.bat` looks for uv, installs it with the standalone installer that Astral
publishes when it is missing, and then runs `run.py`. uv fetches the Python
version and the packages the project pins, so it is the only tool that has to
exist before the first run.

`run.py` offers the data download itself when a file is missing. The licence
notice is printed and the operator answers once, and a closed input counts as a
refusal. The download lives in `fetch()` in `fetch_data.py`, which the script's
own command line calls as well, so both entry points behave the same.

The two data repositories are obtained by whichever route is available. When git
is installed they are cloned with depth one, which keeps `git pull` usable for
updates. Otherwise the repository's zip archive is downloaded, unpacked into a
staging folder that is renamed into place only when the whole archive was
extracted, and any member whose path leaves the target folder is refused. Both
routes leave the same tree on disk, so nothing downstream depends on the choice.
`--no-git` forces the zip route.

The batch file is stored with Windows line endings and marked as not text in
`.gitattributes`, because `cmd` can lose its place at a label in a file with
Unix endings.

## Consequences
A person with the game and no programming background downloads the repository as
a zip file, unpacks it and double clicks one file. The first run takes several
minutes and several gigabytes, mostly PyTorch, and says so.

The data licences are still shown before anything is fetched, and nothing is
redistributed, which keeps the position ADR 0017 and the README describe.

Running the launcher on a machine that has never seen the project has been
tested only on the machine it was written on. The zip route was exercised against
the real GitHub archive of this repository and against a synthetic archive with a
hostile path, and the full first run on a clean Windows account remains to be
done.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Recorded the one click setup and the two routes for the data | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-30 |
