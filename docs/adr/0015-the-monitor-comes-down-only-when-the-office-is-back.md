# ADR 0015: The Monitor Comes Down Only When the Office Is Back on Screen

## Status
Accepted. Extends ADR 0014, which decided when the tablet rises but said nothing about how it is put away. Amended on 2026-10-01, when the office reference was replaced by the camera map as the evidence the tablet is up.

## Context
The 2026-09-17 night ended with the operator lowering the tablet by hand. At 17:50:47 DNp09 reached the bound and `open_camera` was issued in the same second as a right light check, two acts the game cannot run together because the office buttons sit behind the tablet. Six seconds later `close_camera` was issued and the loop marked the tablet as down without checking the screen. The gesture had missed, and one second later the office reference was recaptured on a timer, with the tablet in it. From there the fly read the tablet as the office and the office as the tablet, drove the inhibitors at full rate once the operator lowered it by hand, and every remaining light check came from the starvation guard.

The first fix closed the lowering into a loop and refused to recapture the office reference while the detector still read the tablet. On 2026-10-01 a night went wrong in the same way anyway. The tablet was on screen from the start, the fly believed it was down, it reached for lights and doors with the tablet up, the tablet appeared to open on Show Stage and never switch to CAM 1C, and a door reopening was clicked onto the tablet and never reached the game. The right eye had read the camera map as a threat in the first minute, and the inhibitors were not driven once in 682 frames.

Measuring the detector against the game explained it. Over eighteen frames of a live night, the centre patch read 377 to 893 MSE against the office reference with the tablet up on four different cameras, under the 1200 trigger, and 1359 with nothing more than the office turned to the right, over it. The detector was close to a coin toss, and once it misread a single lowering, the guard that protects the reference had nothing true to check against. `centre_view` did not help either, because FNAF scrolls the office for as long as the cursor sits outside a central band, so the reference was captured while the view was still moving and read 679 against itself.

The gestures were measured on the same night. A cursor teleported onto the bar raised the tablet, but the same teleport did not lower it, and the slide that `close_camera` used crosses the bar in about 16 ms and was ignored on one of two tries. A slide down onto the bar that ends with a few small moves on it flipped the tablet eight times out of eight, alternating, with the map gone in under 0.1 s on the way down and visible after 0.2 to 0.3 s on the way up.

## Decision
The fly decides whether the tablet is up from the camera map, not from a picture of the office. The map region, x 820 to 1240 and y 345 to 680 in the 1280x720 reference layout, is captured with the eye patches, scaled back to that layout, and thresholded at a grey level of 200. Every closed white contour the size of a camera button, 40 to 75 by 25 to 45 pixels and at least 60 percent filled, counts once, and a contour inside one already counted does not. The FNAF 1 map has eleven buttons. The tablet is up when the last three frames all show at least six of them and down when all three show fewer, and in between the fly does not know. On the live frames this count read eleven in all eleven tablet frames and zero in all seven office frames, whichever way the office faced. Nothing is captured as a reference, so there is nothing that can be poisoned.

There is one gesture, `flip_tablet`, a slide from y 540 down onto the bar followed by four small moves on it, and the controller keeps no opinion about the tablet. `put_tablet` checks the screen first and does nothing if the tablet is already where it is wanted, then flips and waits up to `flip_confirm_sec` for the map to agree. Raising works the same way, so the fly only believes the tablet is up once the map is on screen, and a raise the game ignored is reported and dropped. A lowering that is not confirmed is retried every `lower_retry_sec`, and lowering it by hand works because the screen is what the fly believes.

A camera map on screen while the fly believes the tablet is down is put away, and the report counts it. The inhibitors follow the map rather than the fly's belief, light checks wait until no map is on screen, and the door logic presses nothing while it is there. A night therefore starts by making sure the tablet is down, before any light or door is touched.

The two motor programs stay mutually exclusive as before. The camera decision runs first, a look cannot be requested while a raise or a lowering is in flight, and the tablet does not rise while a look is queued or running.

## Consequences
- A single missed gesture no longer inverts the night. The worst case is a raise that is dropped or a lowering that takes another three seconds, and the report shows both under the tablet gestures missed.
- The capture loop counts contours on a 420 by 335 grey image every pass, which is cheap next to the screen grabs it already makes.
- The detector depends on the FNAF 1 map drawing eleven white-bordered buttons at a fixed place on screen. A different game version or a mod that moves the map would need the region and the button size measured again, and `debug_camera.py` prints the live count for that.
- `centre_view`, `nudge_camera_bar`, the office reference and its recapture are gone, and so is the warning about a stale office reference, which described a failure that can no longer happen.
- The DNp04 escape drops the tablet, waits for the map to leave the screen and only then closes the door, so a door click can no longer land on the tablet.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Tablet lowering closed into a loop and the office reference protected | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-17 |
| 1.1 | Editorial pass for consistency with the rest of the documentation | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-18 |
| 1.2 | Replaced the office reference with the camera map as the evidence for the tablet, and a single gesture confirmed on screen | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
