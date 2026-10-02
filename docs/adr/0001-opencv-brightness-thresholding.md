# 0001. Use Grayscale Brightness Thresholding for Threat Detection

## Status
Accepted. Amended on 2026-10-01, when the single empty-hallway reference and its MSE threshold were replaced by a bank of calibrated views.

## Context
The project requires detecting an animatronic at either door in FNAF 1. Exact RGB signatures did not survive screen capture, with compression, purple shifts and the BGR order of `mss` all moving the values, and a full-screen object detector would have competed for CPU with the 138,000-neuron simulation. The first version read the mean brightness of a 10x10 box at Bonnie's spawn point. It was later replaced by the mean squared error between each hallway patch and a reference of that hallway captured empty with the light on, with a threat declared above 1500.

That threshold could never see an animatronic. A live night on 2026-10-01 recorded the exact frames the eye compared while Bonnie stood lit in the left doorway, and he was 124 from the empty reference. The game is dark, Bonnie is a dark figure on a dark background, and the MSE averages his difference over the whole 481x481 patch. Every detection the project had logged above 1500 turned out to be something bright and large covering the eye, the camera tablet, the game over static or another window. The same recording showed that the hallway light flickers, and a flicker frame sits 149 from the lit reference, further than Bonnie. No threshold on the distance to one reference separates the two.

The recording also showed that FNAF draws each hallway from a small fixed set of pre-rendered images. An empty lit hallway matched its reference at exactly zero on every frame, the flicker frame was always the same image, and on the right side the flicker frame is the light-off frame. Bonnie was 118 from the nearest of those views.

The eye also depended on a light whose state nobody checked. The controller toggled each light from what it believed, so a light that was already on when the night began was switched off by the click meant to switch it on, and the fly then looked at a dark hallway for the rest of the night without knowing.

## Decision
Each hallway is compared against a bank of views instead of one reference. The live calibration, run at midnight when both hallways are empty, records each side with the door open and with the door closed, first with the light on for `reference_sweep_sec`, long enough to catch the flicker, and then with the light off. A frame enters the bank only when it differs from every frame already there by more than `bank_tolerance_mse`. The banks are cached together with an index and the layout fingerprint, and a cache without them forces a new calibration.

The distance of a frame is its MSE to the nearest view in the bank for the door's current state, and the evidence for a hallway is the median of those distances over the frames in the buffer, so one odd frame cannot raise or hide a threat. The threshold is 40, a third of the 118 measured for Bonnie and far above the zero every empty view reads, and the tuning range stops at 100 so it cannot be set where Bonnie would disappear again. Each frame's distance is computed once and reused while it stays in the buffer.

The light button is read off the screen. It measured 93 to 97 in grey level off and 186 to 196 on, and the fly treats it as lit above 140. After asking for a light, the fly reads the button twice 80 ms apart and presses it again only when both readings disagree, at most twice, and the press records the state the screen confirmed rather than flipping the controller's belief. A light that will not come on is logged, which in FNAF 1 means an animatronic is already in the office or the power is gone.

## Consequences
- The eye detected Bonnie live at 118 against the new threshold and closed the left door, the first animatronic among all the threat images the project has saved. Replayed through the new code, the recorded frames gave 17 detections out of 17 windows with Bonnie in the doorway and none out of 52 empty windows.
- The first night after the change spends about 70 seconds calibrating with both doors briefly closed and no hallway watched, which is long enough on a continued night for an animatronic to walk in. One recorded night was lost that way.
- The banks are images of the operator's own game, kept under `logs/` and never committed.
- Chica in the right window and Bonnie's shadow behind a closed left door have not been measured against the bank yet. Both thresholds start at 40, and `measure_door_window.py` measures the closed views.
- The light check adds up to a few hundred milliseconds to a look when a correction is needed and nothing when the light is where the controller believes it is.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---------|-------------|-----------|------|-------------|-------------|
| 1.0 | Initial version | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 |
| 1.1 | Replaced the single reference with a bank of calibrated views, measured the threshold against Bonnie, and checked the light on screen | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
