import argparse
import glob
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'src'))

import config
from env import desktop
import launcher
from scripts import fetch_data

_log = logging.getLogger('run')

STORE_NOTE = """
Five Nights at Freddy's is a commercial game by Scott Cawthon and is not part of
this project. Buy it from Steam or itch.io. A copy outside Steam is opened
through GameLauncher.executable in config.py. Without the game, use --replay to
watch a recorded night instead.
"""


def _latest_trace() -> str | None:
    folder = os.path.join(config.PROJECT_ROOT, 'logs', 'traces')
    traces = sorted(glob.glob(os.path.join(folder, 'trace_*.jsonl')))
    return traces[-1] if traces else None


def _report_platform():
    _log.info('platform backend: %s', desktop.name)
    if desktop.name == 'headless':
        _log.info('no display was found, so only the replay and verify paths will work')
    elif desktop.name == 'linux':
        _log.info('X11 backend in use, Wayland sessions are not supported')


def cmd_verify() -> int:
    from scripts import verify_connectome
    verify_connectome.main()
    return 0


def cmd_replay(trace: str | None) -> int:
    import replay as replay_module

    path = trace or _latest_trace()
    if path is None:
        _log.error(
            'no recorded night was found under logs/traces. Run a night first, or point '
            '--replay at a trace file.'
        )
        return 1
    print(replay_module.report(replay_module.replay(path)))
    return 0


def _choose(session, mode: str | None):
    if mode:
        session.choose(mode)
        return None
    window = launcher.LauncherWindow(session)
    if not window.open():
        launcher.ask_in_terminal(session)
        return window
    session.chosen.wait()
    return window


def cmd_play(mode: str | None) -> int:
    import main as main_module

    if not fetch_data.ready():
        fetch_data.print_status()
        if not fetch_data.fetch():
            _log.error('the connectome data is incomplete, the fly cannot start without it')
            return 1

    if desktop.name == 'headless':
        _log.error('playing needs a desktop session, there is no display here')
        return 1

    session = launcher.LauncherSession()
    window = _choose(session, mode)

    if session.mode == launcher.MANUAL:
        if window:
            window.close(linger_sec=1.5)
        main_module.main()
        return 0

    if not launcher.open_game(session):
        if window:
            window.close(linger_sec=4.0)
        print(STORE_NOTE)
        return 1
    if window:
        window.close(linger_sec=1.5)
    launcher.leave_fullscreen(session)
    main_module.main(begin_night=launcher.night_starter(session))
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    parser = argparse.ArgumentParser(description='Run Fly-NAF, or one of the ways to inspect it.')
    parser.add_argument('--verify', action='store_true', help='check the connectome and exit')
    parser.add_argument('--replay', nargs='?', const='', metavar='TRACE',
                        help='replay a recorded night through the brain, no game needed')
    parser.add_argument('--check-data', action='store_true', help='report which data files are present')
    start = parser.add_mutually_exclusive_group()
    start.add_argument('--new', dest='mode', action='store_const', const=launcher.NEW,
                       help='open the game and start a new game, skipping the launcher window')
    start.add_argument('--continue', dest='mode', action='store_const', const=launcher.CONTINUE,
                       help='open the game and continue the saved night, skipping the launcher window')
    start.add_argument('--manual', dest='mode', action='store_const', const=launcher.MANUAL,
                       help='skip the launcher and start the night yourself during the countdown')
    args = parser.parse_args()

    _report_platform()

    if args.check_data:
        fetch_data.print_status()
        return 0 if fetch_data.ready() else 1
    if args.verify:
        return cmd_verify()
    if args.replay is not None:
        return cmd_replay(args.replay or None)
    return cmd_play(args.mode)


if __name__ == '__main__':
    raise SystemExit(main())
