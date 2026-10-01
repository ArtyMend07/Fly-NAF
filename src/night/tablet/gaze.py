class TabletGaze:
    def __init__(self, cameras: tuple, first_camera: str, raise_settle_sec: float,
                 switch_settle_sec: float):
        self._cameras = {camera.name: camera for camera in cameras}
        self._first = first_camera
        self._raise_settle = raise_settle_sec
        self._switch_settle = switch_settle_sec
        self.camera = None
        self.readable_at = 0.0
        self._pursued = False

    def spec(self, name: str | None = None):
        return self._cameras.get(name or self.camera)

    def on_raised(self, now: float) -> str:
        self.camera = self._first
        self.readable_at = now + self._raise_settle
        self._pursued = False
        return self.camera

    def on_lowered(self):
        self.camera = None
        self._pursued = False

    def readable(self, now: float) -> bool:
        return self.camera is not None and now >= self.readable_at

    def pursue(self, now: float, explore_fired: bool) -> str | None:
        current = self.spec()
        if current is None or current.pursue_to is None or self._pursued:
            return None
        if not explore_fired or not self.readable(now):
            return None
        self._pursued = True
        self.camera = current.pursue_to
        self.readable_at = now + self._switch_settle
        return self.camera
