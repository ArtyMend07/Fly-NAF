import argparse
import os

from flynaf import config, recorder
from flynaf.audit import report
from flynaf.env.frame_recorder import frames_folder


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Audit a night recorded with run.py --frames: power by component, doors against '
                    'what the fly believed and what each look at the cove read.',
    )
    nights = range(1, len(config.NIGHT_AUDIT.night_drain_interval_sec) + 1)
    parser.add_argument('night', type=int, choices=nights, help='the night played, which sets its passive drain')
    parser.add_argument('--trace', help='the trace to audit, the latest under logs/traces by default')
    parser.add_argument('--frames', help='the frames recorded with it, found from the trace name by default')
    args = parser.parse_args()

    trace = args.trace or recorder.latest_trace()
    if trace is None:
        print('there is no trace under logs/traces')
        return 1
    folder = args.frames or frames_folder(trace)
    if not os.path.isdir(folder):
        print(f'no frames at {folder}, the night has to be played with run.py --frames')
        return 1
    audit = report.audit_night(trace, folder, args.night)
    print(report.describe(audit))
    print(f'\nsaved to {report.save(audit)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
