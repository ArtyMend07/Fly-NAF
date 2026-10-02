import argparse
import time

from flynaf import clock, config
from flynaf.env.overlay import anchor_to_game
from flynaf.env.tablet_feed import TabletFeed
from flynaf.night.state import SensoryState
from flynaf.night.tablet.senses import TabletSenses


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Live tablet levels for one camera, to fit the spans in TabletVision.',
    )
    parser.add_argument('camera', choices=[button.name for button in config.TABLET_VISION.cameras])
    parser.add_argument('--seconds', type=float, default=60.0)
    args = parser.parse_args()

    anchor_to_game()
    feed = TabletFeed()
    feed.activate()
    input(f'raise the tablet on CAM {args.camera} with nothing in view, then press Enter ')
    if not feed.capture_reference(args.camera):
        print('no frames arrived from the tablet patch')
        return 1

    state = SensoryState(camera_open=True, tablet_camera=args.camera)
    senses = TabletSenses(feed)
    print('watching, bring something into view. Ctrl+C stops.')
    deadline = clock.now() + args.seconds
    try:
        while clock.now() < deadline:
            now = clock.now()
            contrast = feed.contrast(args.camera) or 0.0
            levels = senses.read(state, now)
            shown = '  '.join(f'{name} {level:.2f}' for name, level in levels.items())
            print(f'\rcontrast {contrast:8.0f}  noise {feed.noise(args.camera):6.0f}  {shown}   ', end='')
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
