# Phase 1: Experimental Observations

This document records empirical observations discovered during the execution and testing of Phase 1. These are not formal scientific claims, but field notes on how the simulated biology and the game environment interacted.

## 1. The "Shadow Trap" Calibration
During vision calibration, it was observed that turning on the in-game hallway light did not trigger the brightness threshold (`> 50.0`) at the target coordinates (X=425, Y=486). 
**Observation:** The game utilizes a directional light cone. The calibrated pixel resides in the shadow zone of the doorway. The brightness only spikes when an actual 3D model (the animatronic) physically steps into the light cone and reflects the light into the shadow zone. 
**Impact:** This naturally immunizes the system against false positives caused by the player turning on the light to check the hallway.

## 2. In-Game Viewport Panning Drift
Initial execution resulted in the OS mouse clicking slightly off-target, despite using absolute `SetCursorPos` coordinates.
**Observation:** The game environment features a "pan" mechanic where the camera slides based on mouse position. If the viewport is not pinned to the absolute maximum left boundary (by slamming the mouse to the edge of the screen) during both the calibration phase and the execution phase, the physical UI elements drift horizontally. A discrepancy of ~66 pixels was observed between two calibration attempts simply due to camera panning.
**Impact:** The user must ensure the in-game camera is rigidly locked to the visual boundaries to guarantee pixel-perfect OS clicks.

## 3. Biological Inhibitory Absorption
An *in-silico* test (`analyze_pathways.py`) was run to trace the signal from the Sugar GRNs (sensory) to the P9 neurons (motor).
**Observation:** Despite injecting a biologically maximum saturation (10,000 Hz, equating to a 1.0 firing probability per step) into the sensory neurons for 100 milliseconds, the signal failed to reach the motor cortex. Out of 138,639 neurons, the sensory burst awakened exactly 611 interneurons, but the activation wave died out completely (0 spikes at P9).
**Impact:** This empirically validates the robust inhibitory filtering of the fly's connectome. The biological network does not allow a simple "sugar" stimulus to trigger a violent leg contraction reflex. This necessitated the Phase 1 "Bypass" (ADR-003) and mandates the Graph Search routing planned for Phase 2.
