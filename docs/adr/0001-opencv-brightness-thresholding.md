# 0001. Use Grayscale Brightness Thresholding for Threat Detection

## Status
Accepted

## Context
The project requires detecting the appearance of an animatronic (Bonnie) at the left door in the FNAF 1 game environment. Initial attempts relied on capturing the exact RGB color signature of the animatronic. However, dynamic video rendering and screen capturing can distort RGB values (e.g., color compression, shifts in purple hues, and BGR/RGB inversions in the `mss` library). Additionally, performing full-screen Object Detection (like YOLO) would consume heavy CPU cycles, competing directly with the 138,000-neuron PyTorch biological simulation. 
I needed a detection mechanism that is CPU-agnostic, immune to minor color shifts, and highly precise.

## Decision
I will use OpenCV grayscale brightness thresholding (measuring `np.mean(gray)`) limited to a hardcoded 10x10 pixel bounding box targeted exactly at the animatronic's spawn coordinate. If the brightness exceeds 50.0 points, the system registers a threat. 
Because the FNAF hallway spotlight does not directly illuminate this specific edge pixel when the hall is empty, the brightness remains near 0 even when the light is turned on. It only spikes when the animatronic physically steps into the light cone and reflects light onto the target pixel.

## Consequences
**Positive:**
- CPU usage for vision is effectively 0%, leaving maximum resources for PyTorch.
- Immune to RGB color shifts, BGR library bugs, and video rendering artifacts.
- Immune to false positives from just turning on the light (due to the shadow zone calibration).

**Negative:**
- Highly fragile to in-game camera panning or window resizing. If the absolute coordinates shift by even a few pixels, the system will target a dead zone and fail.
- Requires recalibration if the user switches monitors or display scaling.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---------|-------------|-----------|------|-------------|-------------|
| 1.0 | Initial version | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-09-02 |
