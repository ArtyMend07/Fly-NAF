import config


class AdaptiveSignal:
    def __init__(self, baseline_tau_frames: float, scale_tau_frames: float):
        self._baseline_tau = baseline_tau_frames
        self._scale_tau = scale_tau_frames
        self._baseline = None
        self._scale = 0.0
        self._seen = 0.0

    def update(self, value: float, frames: float) -> float:
        if self._baseline is None:
            self._baseline = value
        self._seen += frames

        baseline_keep = self._keep(self._baseline_tau, frames)
        self._baseline = self._baseline * baseline_keep + value * (1.0 - baseline_keep)
        deviation = value - self._baseline

        scale_keep = self._keep(self._scale_tau, frames)
        self._scale = self._scale * scale_keep + abs(deviation) * (1.0 - scale_keep)
        return deviation / (self._scale + 1e-6)

    def _keep(self, tau_frames: float, frames: float) -> float:
        steady = (1.0 - 1.0 / tau_frames) ** frames
        if self._seen <= 1.0:
            return 0.0
        return min(steady, max(0.0, 1.0 - frames / self._seen))


def _frames(elapsed_sec: float, fps: float) -> float:
    return min(50.0, max(0.0, elapsed_sec * fps))


def _integrate(sum_so_far: float, gain: float, signal: float, leak: float, frames: float) -> float:
    decay = leak ** frames
    span = (1.0 - decay) / (1.0 - leak)
    return sum_so_far * decay + gain * signal * span


class ExploreDrive:
    def __init__(self, params=None, nominal_fps: float | None = None):
        self._p = params or config.EXPLORE_DYNAMICS
        self._fps = nominal_fps or config.SIMULATION_PARAMS.target_fps
        self._signal = AdaptiveSignal(self._p.baseline_tau_frames, self._p.scale_tau_frames)
        self.drive = 0.0
        self.commanded = False

    @property
    def tension(self) -> float:
        return min(1.0, self.drive / self._p.bound)

    @property
    def wants_monitor(self) -> bool:
        return self.drive >= self._p.bound

    @property
    def spent(self) -> bool:
        return self.drive <= self._p.bound * self._p.release_ratio

    def update(self, membrane: float, fired: bool, elapsed_sec: float) -> float:
        p = self._p
        frames = _frames(elapsed_sec, self._fps)
        deviation = self._signal.update(membrane, frames)
        gain = p.gain_ratio * (1.0 - p.drive_leak_per_frame) * p.bound

        self.drive = _integrate(self.drive, gain, deviation, p.drive_leak_per_frame, frames)
        self.commanded = bool(fired)
        if fired:
            self.drive = max(self.drive, p.bound)
        self.drive = max(0.0, self.drive)
        return self.drive


class SearchDrive:
    def __init__(self, sensory_span: int, params=None, nominal_fps: float | None = None):
        self._p = params or config.SEARCH_DYNAMICS
        self._fps = nominal_fps or config.SIMULATION_PARAMS.target_fps
        self._span = max(1, sensory_span)

        self._signal = AdaptiveSignal(self._p.baseline_tau_frames, self._p.scale_tau_frames)
        self._drift_sum = 0.0
        self._evidence_sum = 0.0
        self._habituation_sum = 0.0
        self._habituation = {'left': 0.0, 'right': 0.0}
        self._last_look = {'left': None, 'right': None}
        self.reason = None
        self.last_drive = 0.0

    @property
    def drive(self) -> float:
        return self._drift_sum + self._evidence_sum + self._habituation_sum

    @property
    def tension(self) -> float:
        return min(1.0, abs(self.drive) / self._p.bound)

    def update(
        self,
        membrane_diff: float,
        left_count: float,
        right_count: float,
        elapsed_sec: float,
        now: float,
        can_act: bool,
    ) -> str | None:
        p = self._p
        frames = _frames(elapsed_sec, self._fps)

        if self._last_look['left'] is None:
            self._last_look = {'left': now, 'right': now}

        drift = self._signal.update(membrane_diff, frames)

        evidence = (left_count - right_count) / self._span
        evidence = max(-1.0, min(1.0, evidence)) * p.evidence_gain

        habituation_keep = p.habituation_leak_per_frame ** frames
        for side in self._habituation:
            self._habituation[side] *= habituation_keep
        imbalance = self._habituation['left'] - self._habituation['right']

        gain = p.gain_ratio * (1.0 - p.drive_leak_per_frame) * p.bound
        leak = p.drive_leak_per_frame
        self._drift_sum = _integrate(self._drift_sum, gain, drift, leak, frames)
        self._evidence_sum = _integrate(self._evidence_sum, gain, evidence, leak, frames)
        self._habituation_sum = _integrate(
            self._habituation_sum, gain, -p.habituation_gain * imbalance, leak, frames
        )

        if not can_act:
            return None

        starved = self._starved_side(now)
        if starved is not None:
            self.reason = 'guard'
            return self._commit(starved, now)

        drive = self.drive
        if abs(drive) >= p.bound:
            side = 'left' if drive > 0 else 'right'
            self.reason = (
                'evidence'
                if abs(self._evidence_sum) > abs(self._drift_sum)
                else 'drift'
            )
            return self._commit(side, now)
        return None

    def _starved_side(self, now: float) -> str | None:
        waits = {side: now - t for side, t in self._last_look.items()}
        starved = [side for side, wait in waits.items() if wait >= self._p.starvation_sec]
        if not starved:
            return None
        if len(starved) == 1:
            return starved[0]
        return 'left' if self.drive > 0 else 'right'

    def _commit(self, side: str, now: float) -> str:
        self.last_drive = self.drive
        self._last_look[side] = now
        self._habituation[side] += 1.0
        self._drift_sum = 0.0
        self._evidence_sum = 0.0
        self._habituation_sum = 0.0
        return side
