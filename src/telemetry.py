import time
import os
from datetime import datetime

import config

REFLEX_FRAMES = 10

class ConnectomeTelemetry:
    def __init__(self):
        self.start_time = time.time()
        self.events = []
        self.stats = {
            'left_door_panics': 0,
            'right_door_panics': 0,
            'left_door_releases': 0,
            'right_door_releases': 0,
            'camera_pulls': 0,
            'left_light_saccades': 0,
            'right_light_saccades': 0
        }
        self.door_holds = []
        self.saccade_reasons = {'drift': 0, 'evidence': 0, 'guard': 0}
        self.camera_causes = {'spike': 0, 'drive': 0}
        self.camera_watches = []
        self.camera_release_reasons = {'drive': 0, 'search': 0, 'cap': 0, 'escape': 0}
        self.camera_views = {}
        self.camera_view_causes = {'raise': 0, 'pursuit': 0}
        self.tablet_escapes = {}
        self.look_contrast = {'left': [], 'right': []}
        self.look_frames = []
        self.look_driven = []
        self.engine_frames = 0
        self.inhibited_frames = 0
        self.looking_frames = 0
        self.monitor_stuck = 0
        self.saccade_gaps = []
        self._last_saccade_at = None

    def record_door_panic(self, side: str, cause: str = 'giant fiber'):
        t = time.time() - self.start_time
        self.stats[f'{side}_door_panics'] += 1
        self.events.append(f"[{t:>6.1f}s] Visual threat detected. {cause.capitalize()} fired. {side.capitalize()} door slammed.")

    def record_camera_view(self, camera: str, cause: str):
        t = time.time() - self.start_time
        self.camera_views[camera] = self.camera_views.get(camera, 0) + 1
        if cause in self.camera_view_causes:
            self.camera_view_causes[cause] += 1
        why = 'the tablet came up on it' if cause == 'raise' else 'DNp09 fired and the gaze followed'
        self.events.append(f"[{t:>6.1f}s] Watching CAM {camera}, {why}.")

    def record_tablet_escape(self, side: str, camera: str):
        t = time.time() - self.start_time
        key = f'{camera} {side}'
        self.tablet_escapes[key] = self.tablet_escapes.get(key, 0) + 1
        self.events.append(
            f"[{t:>6.1f}s] DNp04 {side} fired on a looming shape in CAM {camera}. Tablet dropped for the door."
        )

    def record_door_release(self, side: str, held_sec: float):
        t = time.time() - self.start_time
        self.stats[f'{side}_door_releases'] += 1
        self.door_holds.append(held_sec)
        self.events.append(f"[{t:>6.1f}s] Escape drive decayed after {held_sec:.1f}s. {side.capitalize()} door reopened.")

    def record_camera_pull(self, commanded: bool, drive: float):
        t = time.time() - self.start_time
        self.stats['camera_pulls'] += 1
        self.camera_causes['spike' if commanded else 'drive'] += 1
        how = ('DNp09 fired outright' if commanded
               else f'DNp09 drive accumulated to {drive:.2f}')
        self.events.append(f"[{t:>6.1f}s] {how}. Monitor raised for environmental scan.")

    RELEASES = {
        'drive': 'the exploratory drive faded',
        'search': 'the fly wanted to check a hallway',
        'cap': 'the power cap expired',
        'escape': 'something loomed on the camera',
    }

    def record_camera_release(self, watched_sec: float, reason: str):
        t = time.time() - self.start_time
        self.camera_watches.append(watched_sec)
        if reason in self.camera_release_reasons:
            self.camera_release_reasons[reason] += 1
        why = self.RELEASES.get(reason, reason)
        self.events.append(
            f"[{t:>6.1f}s] Monitor lowered after {watched_sec:.1f}s, {why}."
        )

    def record_frame(self, inhibited: bool, looking: bool):
        self.engine_frames += 1
        if inhibited:
            self.inhibited_frames += 1
        if looking:
            self.looking_frames += 1

    def record_look_contrast(self, side: str, mse: float, frames: int, driven: int):
        self.look_contrast[side].append(mse)
        self.look_frames.append(frames)
        self.look_driven.append(driven)

    def record_monitor_stuck(self):
        t = time.time() - self.start_time
        self.monitor_stuck += 1
        self.events.append(
            f"[{t:>6.1f}s] Monitor stayed up after both lowering gestures. Retrying."
        )

    CAUSES = {
        'drift': 'Spontaneous hemispheric drift',
        'evidence': 'What the last look revealed',
        'guard': 'Starvation guard (not the connectome)',
    }

    def record_light_saccade(self, side: str, drive: float, reason: str):
        t = time.time() - self.start_time
        self.stats[f'{side}_light_saccades'] += 1
        if reason in self.saccade_reasons:
            self.saccade_reasons[reason] += 1
        now = time.time()
        if self._last_saccade_at is not None:
            self.saccade_gaps.append(now - self._last_saccade_at)
        self._last_saccade_at = now
        cause = self.CAUSES.get(reason, reason)
        self.events.append(
            f"[{t:>6.1f}s] {cause} drove a {side} light check (search drive: {drive:+.2f})."
        )

    def _write_tablet(self, f):
        f.write("--- What The Tablet Showed ---\n")
        if not self.camera_views:
            f.write(f"{'Cameras watched':<38}: none\n\n")
            return
        views = ', '.join(f'{camera} x{count}' for camera, count in sorted(self.camera_views.items()))
        f.write(f"{'Cameras watched':<38}: {views}\n")
        causes = self.camera_view_causes
        f.write(f"{'Chosen by':<38}: {causes['raise']} on raising, {causes['pursuit']} DNp09 pursuit\n")
        escapes = ', '.join(f'{key} x{count}' for key, count in sorted(self.tablet_escapes.items())) or 'none'
        f.write(f"{'DNp04 escapes from the tablet':<38}: {escapes}\n\n")

    def dump_report(self):
        duration = time.time() - self.start_time
        os.makedirs("logs", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join("logs", f"session_telemetry_{timestamp}.txt")
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=== Connectome Session Report ===\n")
            f.write(f"Session Duration : {duration:.1f} seconds\n")
            f.write(f"Timestamp        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("--- Quantitative Breakdown ---\n")
            f.write(f"Left Door Panics (Bonnie)  : {self.stats['left_door_panics']}\n")
            f.write(f"Right Door Panics (Chica)  : {self.stats['right_door_panics']}\n")
            f.write(f"Left Door Releases         : {self.stats['left_door_releases']}\n")
            f.write(f"Right Door Releases        : {self.stats['right_door_releases']}\n")
            if self.door_holds:
                mean_hold = sum(self.door_holds) / len(self.door_holds)
                f.write(f"Mean Door Hold             : {mean_hold:.1f}s\n")
                f.write(f"Total Door-Closed Time     : {sum(self.door_holds):.1f}s\n")
            f.write(f"Spontaneous Camera Pulls   : {self.stats['camera_pulls']}\n")
            if self.camera_watches:
                watches = len(self.camera_watches)
                mean = sum(self.camera_watches) / watches
                f.write(f"Mean Monitor Watch         : {mean:.1f}s, {sum(self.camera_watches) / max(duration, 1.0) * 100:.0f}% of the night blind\n")
                f.write(f"Monitor Raised By          : {self.camera_causes['spike']} DNp09 spikes, {self.camera_causes['drive']} accumulated drive\n")
                by = self.camera_release_reasons
                f.write(f"Monitor Lowered By         : {by['drive']} drive faded, {by['search']} hallway won, {by['cap']} power cap, {by['escape']} looming escape\n")
            f.write(f"Left Light Checks          : {self.stats['left_light_saccades']}\n")
            f.write(f"Right Light Checks         : {self.stats['right_light_saccades']}\n\n")

            f.write("--- Who Decided To Look ---\n")
            looks = sum(self.saccade_reasons.values())
            for reason, count in self.saccade_reasons.items():
                share = 100.0 * count / looks if looks else 0.0
                f.write(f"{self.CAUSES[reason]:<38}: {count:>3} ({share:.0f}%)\n")
            if looks:
                brain = looks - self.saccade_reasons['guard']
                f.write(f"{'Brain-driven share':<38}: {100.0 * brain / looks:.0f}%\n")
            if self.saccade_gaps:
                ordered = sorted(self.saccade_gaps)
                median = ordered[len(ordered) // 2]
                f.write(f"{'Interval between looks':<38}: "
                        f"median {median:.1f}s, min {ordered[0]:.1f}s, max {ordered[-1]:.1f}s\n")
            f.write("\n")


            self._write_tablet(f)

            f.write("--- Where The Night Went ---\n")
            if self.engine_frames:
                rate = self.engine_frames / max(duration, 1.0)
                f.write(f"{'Engine rate':<38}: {rate:.1f} frames/sec, "
                        f"{self.engine_frames} frames\n")
                f.write(f"{'Inhibitors driven':<38}: "
                        f"{100.0 * self.inhibited_frames / self.engine_frames:.0f}% of frames (silences both descending neurons)\n")
                f.write(f"{'Busy with a light':<38}: "
                        f"{100.0 * self.looking_frames / self.engine_frames:.0f}% of frames (the monitor cannot rise then)\n")
            f.write("\n")

            f.write("--- What The Eye Measured ---\n")
            threshold = config.FORAGING_PARAMS.mse_threshold
            f.write(f"{'Threat threshold (MSE)':<38}: {threshold:.0f}\n")
            for side in ('left', 'right'):
                readings = self.look_contrast[side]
                if not readings:
                    f.write(f"{side.capitalize() + ' hallway':<38}: never looked at\n")
                    continue
                ordered = sorted(readings)
                median = ordered[len(ordered) // 2]
                crossed = sum(1 for mse in readings if mse > threshold)
                f.write(f"{side.capitalize() + ' hallway':<38}: "
                        f"{len(readings)} looks, median {median:.0f}, peak {ordered[-1]:.0f}, "
                        f"{crossed} over the threshold\n")
            if self.look_frames:
                spans = sorted(self.look_frames)
                f.write(f"{'Engine frames per look':<38}: "
                        f"median {spans[len(spans) // 2]}, min {spans[0]}, max {spans[-1]}\n")
            if self.look_driven:
                driven = sorted(self.look_driven)
                enough = sum(1 for d in self.look_driven if d >= REFLEX_FRAMES)
                f.write(f"{'Frames the eye drove the cluster':<38}: "
                        f"median {driven[len(driven) // 2]}, peak {driven[-1]}, {enough} long enough to slam a door\n")
            f.write("\n")

            f.write("--- Chronological Event Log ---\n")
            for evt in self.events:
                f.write(evt + "\n")
                
        return filepath
