# Experiment 11: A Browser Profile For Every Night

## What I Saw

The launcher opens the game fullscreen, the connectome loads, the brain panel
appears, and the game drops to the taskbar. Every time. When I dragged it back
the mouse was aiming at coordinates measured on a window that no longer
existed, so the fly spent the night clicking on my desktop.

The first explanation was the obvious one. Windows minimises an exclusive
fullscreen game the moment any other window takes the foreground, and a fresh
browser window takes the foreground when it is created. So I launched the
browser with `SW_SHOWNOACTIVATE` in its `STARTUPINFO`, which asks Windows to
show the window without activating it, and ran the tests, which passed.

The next run produced two Edge windows with their normal title bars, floating
at default sizes in default places, and the game minimised underneath them.
Not a partial improvement. Nothing had changed at all.

## The Flag That Was Not Reaching Anyone

The detail that gave it away was not the focus. The windows were also ignoring
`--window-position` and `--window-size`, which had worked for weeks. A browser
that ignores every flag at once is not misreading one of them, it is not
reading them.

Chromium keeps one process per profile directory. A second launch pointed at a
profile that is already open does not open anything itself. It forwards its
command line to the process that owns the profile and exits a few milliseconds
later, and the owner opens a window with its own defaults. Every flag I had
been adding was being handed to a process that was about to die.

A process listing found the owner. Nine `msedge.exe` processes, all rooted in
one parent, all pointing at `logs/brain_view_profile`, left over from earlier
test runs that day. They were orphans, because Windows does not kill a child
when its parent dies, and a run stopped from the task manager left its browser
behind. So one bug was hiding the other. The orphan owned the profile, and the
profile swallowed the fix.

## Why A Fresh Profile

There were two ways out. Keep the fixed profile and kill whatever holds it
before each launch, or give every launch a profile nobody else can hold. The
first meant finding and killing browser processes by matching a path in their
command line, and at that point the orphans were the normal state of affairs,
since nothing tied the browser's life to the run yet. The second made each
launch independent of whatever the last one left behind, which is also what
Selenium and Playwright do for exactly this reason. So every launch got its own
directory from `tempfile.mkdtemp`, the flags started arriving, and the game
stayed in front.

It fixed the bug. It also started quietly filling the disk.

## The Bill

A Chromium profile is not an empty folder. The first launch writes caches, a
GPU shader cache, crash reporting state and a small database or two, and it
comes to about 60 MB. Nothing ever deleted them. By the time I went looking
there were ten `flynaf_*` directories in `%TEMP%` adding up to 460 MB, from a
single afternoon of testing. At one night per launch, a hundred nights of
testing is six gigabytes of browser profiles for a panel that shows dots. Not
quite exploding the PC, but heading that way at 60 MB a night.

The fresh profile had a second side effect that was visible instead of silent.
To Edge a new profile is a first run, and on a first run it signs into the
Windows account and puts up a sync consent bubble, which landed squarely on
top of the panel with my e-mail address in it. I tried four flag sets against
the same page and captured the screen for each. The bare launch reproduced the
bubble exactly. `--disable-sync` removed it, and so did `--inprivate` and
`--guest`, but only `--disable-sync` leaves the rest of the profile behaving
normally, so that is the one that went in.

## Knowing When A Profile Is Dead

Deleting the profiles is easy. Not deleting the one a live panel is using is
the part that matters, since a second run of the project may be open. Chromium
already tracks this. On Windows it holds a file called `lockfile` open inside
the profile for as long as the browser runs, so the file cannot be removed
while a browser is alive and can be once it is gone. On Linux it keeps a
`SingletonLock` link whose target ends in the owner's process id. The sweep
tries the lock and only removes the directory when nobody answers. I checked it
against a live Edge, which kept its profile, and against the same Edge after
killing it, which lost it. The sweep runs before every launch and after the
panel closes.

The orphans were fixed separately, and that fix is what makes the fresh
profiles safe to keep. On Windows the browser now starts inside a job object
that kills it when the Python process ends, however it ends, and on Linux the
kernel does the same through `PR_SET_PDEATHSIG`. I tested both by killing the
parent outright with `os._exit` and `SIGKILL`. ADR 0021 has the details.

## What I Take From It

I was fixing focus, and the real bug was which process got the flags. The
tests passed through all of it because they mock the process launch, which is
precisely the thing that was broken. The fix itself was right, but it came with
a cost I did not notice until I measured it. Measuring is cheap; I should have
looked in `%TEMP%` the day I started writing there.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | The swallowed browser flags, the fresh profile per launch, and the 460 MB it cost | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-28 |
