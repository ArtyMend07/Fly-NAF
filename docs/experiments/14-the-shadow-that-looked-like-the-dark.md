# Experiment 14: The Shadow That Looked Like The Dark

The doors finally reopened on their own (ADR 0011), and the first thing the fly did with that was reopen the left door with Bonnie standing right behind it. His shadow was in the window, I could see it, and the fly looked at the window with the light on and decided the hallway was empty. Then it opened the door and died (Bonnie was very happy about it).

The closed-door threshold was 40, copied from the open door, and ADR 0011 already admitted it had never been fitted on a shadow. So the plan was simple, measure the window with the door closed, once empty and once with Bonnie, and put the threshold in between.

### Measuring It Badly, Twice

The empty reading came out at exactly 0 on every frame. FNAF draws the lit window behind a closed door from one pre-rendered image, so an empty window is pixel for pixel the reference. Good start.

Then I left a script closing the door, turning the light on every couple of seconds and waiting for Bonnie. It read 371 over and over, which looked like a lot of Bonnie for a hallway with nobody in it. The door was open. The controller toggles each door from what it believes, the previous script had left the door shut, and the new process started believing it was open, therefore the click meant to close it opened it. I had been measuring an open hallway against closed-door references for minutes (lol).

The second attempt checked the door button colour on screen before every click, which is the right idea, except it sampled a fixed point and the button is only there when the office is turned to the left. It read black, decided nothing was where it should be and kept clicking. At that point I stopped letting a script touch the game at all. I played the night myself, handled Foxy and the right door, and a second script only watched the screen and saved every frame while the left light was on.

### Bonnie Measured 2

When Bonnie came, I closed the door and held the light on his shadow. Twenty-five readings, all of them 2 against the closed-door bank, under a threshold of 40. For the eye he basically did not exist.

My first guess was the box. The left eye reads a 481 pixel square from x 0 to 480 of the game, and most of that square is the door and its buttons. Bonnie's shadow sits from x 420 to 517 and y 263 to 541, so 42 percent of it falls outside the box, and the part inside is diluted by everything that does not change. Against the empty window, the shadow inside the box measured 16. That explains why 40 could never catch him, but it does not explain 2.

My second guess was that the calibration had recorded Bonnie. The bank had three closed-door views and the one he matched at 2, `left_closed_01`, did look different from the empty one in exactly the same place. That turned out to be wrong as well. Inside the window, that view was identical to the view recorded with the light off, MSE 0.0. It was not Bonnie, it was a frame from the lit sweep taken before the light had actually reached the window.

### What The Light Actually Adds

Putting the frames side by side made it obvious. With the door closed, the hallway light adds almost nothing to the window, just a thin vertical streak of light around x 450. Everything else in the window is the office itself, the same with the light on or off. When Bonnie stands there, his body covers that streak, and his head shows up as a dark shape a bit further right, mostly past the edge of the eye box.

So inside the old box, a dark window and Bonnie are the same picture. The bank held a dark window as a normal view, and the comparison picks the nearest view, therefore Bonnie read as normal. The same hole existed from another side too. A look where the light would not come on still counted as a clear look, because a dark window matched the dark views of the bank.

### What Changed

Behind a closed door the eye now reads the window itself, a rectangle from x 340 to 540 and y 200 to 560 captured on its own, with the whole shadow inside and the door left out. The closed-door bank keeps only the brightest frame of the lit sweep, which is the empty window with the streak in it, and no dark view enters it anymore. On that rectangle Bonnie measures about 77 against the empty window, so the threshold went to 30. A look only clears a door when the light was confirmed on screen. If the light flickers behind a closed door, the fly reads a threat and holds the door a little longer, and I would rather pay that in power than in jumpscares.

### The Night After

The first night with the change recalibrated (the layout had changed) and then did exactly what it should. At 20:59:16 Bonnie showed up in the open doorway at 118 and the giant fiber closed the left door. Thirty seconds later the fly looked at the window behind the closed door, read 95 against 30 and the giant fiber fired again, so the hold was renewed instead of the door opening into him. At 21:00:02 it looked again, read 0, and only then released the door, after 46.5 seconds. Chica on the right read 482 behind the closed right door and kept it shut the same way.

It got close to the end of night 3 and then lost it on the left. At 21:01:12 a look read 118 with the door open, which is Bonnie in the doorway, but the eye was driven on only 1 of 12 frames and the giant fiber never answered, so the door stayed open. Twenty seconds later the left light would not come on, which in FNAF 1 is what happens when an animatronic is already inside the office. I think the light did not jam on its own, the fly missed him by one frame first. Why a doorway reading of 118 drove the eye only once is the next thing to measure, as well as the right window, which still uses the old box until I measure Chica the same way.

| Version | Description | Author(s) | Date | Reviewer(s) | Review Date |
|---|---|---|---|---|---|
| 1.0 | Why the fly reopened into Bonnie, the dark window hiding his shadow, the window rectangle and the first night with it | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 | [Artur Mendonça Arruda](https://github.com/ArtyMend07) | 2026-10-01 |
