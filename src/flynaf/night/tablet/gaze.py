class TabletGaze:
    def __init__(self, cameras: tuple, first_camera: str, raise_settle_sec: float):
        self._cameras = {camera.name: camera for camera in cameras}
        self._first = first_camera
        self._raise_settle = raise_settle_sec
        self.camera = None
        self.readable_at = 0.0

    def spec(self, name: str | None = None):
        return self._cameras.get(name or self.camera)

    def on_raised(self, now: float) -> str:
        self.camera = self._first
        self.readable_at = now + self._raise_settle
        return self.camera

    def on_lowered(self):
        self.camera = None

    def readable(self, now: float) -> bool:
        return self.camera is not None and now >= self.readable_at

    def pursued(self, now: float, explore_fired: bool):
        if not explore_fired or not self.readable(now):
            return None
        return self.spec()
