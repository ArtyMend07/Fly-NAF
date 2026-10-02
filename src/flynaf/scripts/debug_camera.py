import time

from flynaf import config
from flynaf.env.overlay import anchor_to_game
from flynaf.env.vision import FNAFVision


def main():
    if not anchor_to_game():
        print('the game window was not found, the 1280x720 layout is read from the top left')
    vision = FNAFVision()
    needed = config.CAMERA_DETECTION.min_buttons
    print(f'the tablet counts as up with {needed} or more camera buttons in view. Ctrl+C to stop.')
    try:
        while True:
            seen = vision.map_buttons()
            verdict = 'UP' if vision.is_camera_up() else 'down' if vision.is_camera_down() else 'changing'
            print(f'\rbuttons {seen}  tablet {verdict:<8}', end='', flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('\nstopped')


if __name__ == '__main__':
    main()
