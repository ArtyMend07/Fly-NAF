import asyncio
import base64
import csv
import dataclasses
import json
import os
import struct
import time
import urllib.parse

import cv2
import numpy as np

from flynaf import config

REGION_OPTIC = 0
REGION_CENTRAL = 1
REGION_SENSORY = 2
REGION_MOTOR = 3

_REGION_BY_SUPER_CLASS = {
    'optic': REGION_OPTIC,
    'visual_centrifugal': REGION_OPTIC,
    'central': REGION_CENTRAL,
    'endocrine': REGION_CENTRAL,
    'sensory': REGION_SENSORY,
    'sensory_ascending': REGION_SENSORY,
    'visual_projection': REGION_SENSORY,
    'ascending': REGION_SENSORY,
    'descending': REGION_MOTOR,
    'motor': REGION_MOTOR,
}


@dataclasses.dataclass(frozen=True)
class PanelFrame:
    gaze: str = '--'
    camera: bool = False
    cam: str | None = None
    gf_l: bool = False
    gf_r: bool = False
    in_l: bool = False
    in_r: bool = False
    look_l: bool = False
    look_r: bool = False
    mse_l: float | None = None
    mse_r: float | None = None
    mse_th: float = 0.0
    eye_l: int = 0
    eye_r: int = 0
    door_l: bool = False
    door_r: bool = False
    figure: float = 0.0
    loom: float = 0.0
    dnp09: bool = False
    dnp04_l: bool = False
    dnp04_r: bool = False


class SpikeFeed:
    def __init__(self, num_neurons: int = 0, tracer=None):
        self.indices = np.empty(0, dtype=np.uint32)
        self.panel = PanelFrame()
        self._seen = np.zeros(num_neurons, dtype=bool)
        self._tracer = tracer
        self.fired_total = 0
        self.spike_total = 0
        self.revision = 0
        self.cascade = None
        self.cascade_revision = 0

    def publish(self, spiking: np.ndarray, panel: PanelFrame | None = None):
        if panel is not None:
            self.panel = panel
        self.indices = np.unique(spiking).astype(np.uint32, copy=False)
        self.spike_total += int(self.indices.size)
        if self._seen.size:
            fresh = ~self._seen[self.indices]
            self.fired_total += int(fresh.sum())
            self._seen[self.indices] = True
        if self._tracer is not None:
            self._tracer.record(self.indices)
        self.revision += 1

    def trace_escape(self, side: str, target: int, sources, door_moved: bool):
        if self._tracer is None:
            return
        cascade = self._tracer.trace(target, sources)
        cascade['side'] = side
        cascade['frame'] = self.revision
        cascade['sources'] = [int(s) for s in sources]
        cascade['door_moved'] = door_moved
        self.cascade = cascade
        self.cascade_revision += 1


def _encode_patch(patch, side: int) -> str | None:
    if patch is None:
        return None
    small = cv2.resize(np.clip(patch, 0, 255).astype(np.uint8), (side, side), interpolation=cv2.INTER_AREA)
    ok, jpeg = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 72])
    return base64.b64encode(jpeg.tobytes()).decode('ascii') if ok else None


def _read_soma_positions(root_ids: list) -> np.ndarray:
    path = os.path.join(config.DATA_DIR, 'soma_coordinates_783.csv')
    first = {}
    with open(path, newline='', encoding='utf-8', errors='replace') as handle:
        reader = csv.reader(handle)
        header = next(reader)
        root_col = header.index('root_id')
        position_col = header.index('position')
        for row in reader:
            root_id = row[root_col].strip()
            if root_id not in first:
                first[root_id] = row[position_col]
    coords = np.full((len(root_ids), 3), np.nan, dtype=np.float32)
    for i, root_id in enumerate(root_ids):
        text = first.get(root_id)
        if text:
            coords[i] = [float(v) for v in text.strip('[]').split()]
    return coords


def _read_brain_mesh():
    path = os.path.join(config.DATA_DIR, 'brain_mesh_flywire.ply')
    if not os.path.isfile(path):
        return None
    with open(path, 'rb') as handle:
        data = handle.read()
    marker = b'end_header\n'
    end = data.index(marker) + len(marker)
    header = data[:end].decode('ascii')
    vertex_count = int(header.split('element vertex ')[1].split()[0])
    face_count = int(header.split('element face ')[1].split()[0])
    vertices = np.frombuffer(data, dtype='<f4', count=vertex_count * 3, offset=end).reshape(-1, 3)
    face_type = np.dtype([('n', 'u1'), ('i', '<u4', 3)])
    faces = np.frombuffer(data, dtype=face_type, count=face_count, offset=end + vertex_count * 12)
    return vertices.astype(np.float32), faces['i'].astype(np.uint32)


def _normalizer(positions: np.ndarray, mesh):
    reference = mesh[0] if mesh is not None else positions[~np.isnan(positions).any(axis=1)]
    low = np.percentile(reference, 0.5, axis=0)
    high = np.percentile(reference, 99.5, axis=0)
    center = (low + high) / 2.0
    scale = float(np.max(high - low) / 2.0) or 1.0

    def apply(points: np.ndarray) -> np.ndarray:
        placed = (points - center) / scale
        placed[:, 1] *= -1.0
        placed[:, 2] *= -1.0
        return placed.astype(np.float32)

    return apply


def _read_regions(root_ids: list) -> np.ndarray:
    candidates = [
        os.path.join(
            os.path.dirname(config.PROJECT_ROOT), 'flywire_annotations',
            'supplemental_files', 'Supplemental_file1_neuron_annotations.tsv',
        ),
        os.path.join(
            config.DATA_DIR, 'flywire_annotations',
            'supplemental_files', 'Supplemental_file1_neuron_annotations.tsv',
        ),
    ]
    path = next((p for p in candidates if os.path.isfile(p)), None)

    by_root = {}
    if path is not None:
        with open(path, newline='', encoding='utf-8', errors='replace') as handle:
            reader = csv.reader(handle, delimiter='\t')
            header = next(reader)
            root_col = header.index('root_id')
            class_col = header.index('super_class')
            for row in reader:
                if len(row) > class_col:
                    by_root[row[root_col].strip()] = row[class_col].strip()

    regions = np.full(len(root_ids), REGION_CENTRAL, dtype=np.uint8)
    for i, root_id in enumerate(root_ids):
        super_class = by_root.get(root_id)
        if super_class in _REGION_BY_SUPER_CLASS:
            regions[i] = _REGION_BY_SUPER_CLASS[super_class]
    return regions


def _read_root_ids() -> list:
    with open(config.COMPLETENESS_CSV, newline='') as handle:
        rows = list(csv.reader(handle))
    return [row[0].strip() for row in rows[1:]]


def build_blobs() -> tuple:
    root_ids = _read_root_ids()
    positions = _read_soma_positions(root_ids)
    regions = _read_regions(root_ids)
    mesh = _read_brain_mesh()
    place = _normalizer(positions, mesh)
    placed = place(np.nan_to_num(positions, nan=0.0))
    placed[np.isnan(positions).any(axis=1)] = 0.0
    geometry = struct.pack('<I', len(root_ids)) + placed.tobytes() + regions.tobytes()
    if mesh is None:
        return geometry, struct.pack('<II', 0, 0)
    vertices, faces = mesh
    outline = struct.pack('<II', len(vertices), len(faces)) + place(vertices).tobytes() + faces.tobytes()
    return geometry, outline


class BrainViewServer:
    def __init__(self, feed: SpikeFeed, eyes=None):
        self._feed = feed
        self._eyes = eyes
        self._geometry = None
        self._outline = None
        self._page = None
        self._server = None
        self._params = config.BRAIN_VIEW
        self._page_height = 0

    def page_height(self) -> int:
        return self._page_height

    async def start(self) -> int:
        self._geometry, self._outline = await asyncio.to_thread(build_blobs)
        self._server = await asyncio.start_server(
            self._handle, '127.0.0.1', self._params.port
        )
        return self._server.sockets[0].getsockname()[1]

    async def close(self):
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            request = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), timeout=5.0)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, ConnectionError):
            writer.close()
            return

        path = request.split(b' ')[1].decode('latin-1') if b' ' in request else '/'
        try:
            if path.startswith('/geometry'):
                await self._send(writer, b'application/octet-stream', self._geometry)
            elif path.startswith('/outline'):
                await self._send(writer, b'application/octet-stream', self._outline)
            elif path.startswith('/stream'):
                await self._stream(writer)
            elif path.startswith('/viewport'):
                self._page_height = _query_int(path, 'h')
                await self._send(writer, b'text/plain', b'')
            else:
                await self._send(writer, b'text/html; charset=utf-8', _load_page())
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            if not writer.is_closing():
                writer.close()

    async def _send(self, writer: asyncio.StreamWriter, content_type: bytes, body: bytes):
        writer.write(
            b'HTTP/1.1 200 OK\r\nContent-Type: ' + content_type
            + b'\r\nContent-Length: ' + str(len(body)).encode()
            + b'\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n'
        )
        writer.write(body)
        await writer.drain()

    async def _stream(self, writer: asyncio.StreamWriter):
        writer.write(
            b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n'
            b'Cache-Control: no-store\r\nConnection: keep-alive\r\n\r\n'
        )
        await writer.drain()

        sent = -1
        sent_cascade = 0
        patches_at = 0.0
        interval = self._params.stream_interval_sec
        ms_per_frame = config.SIMULATION_PARAMS.steps_per_frame * config.NEURAL_PARAMS.dt
        while not writer.is_closing():
            feed = self._feed
            if feed.revision != sent:
                sent = feed.revision
                frame = dataclasses.asdict(feed.panel)
                frame['s'] = base64.b64encode(feed.indices.tobytes()).decode('ascii')
                frame['n'] = feed.revision
                frame['fired'] = feed.fired_total
                frame['spikes'] = feed.spike_total
                frame['ms'] = ms_per_frame
                if feed.cascade_revision != sent_cascade and feed.cascade is not None:
                    sent_cascade = feed.cascade_revision
                    frame['c'] = feed.cascade
                now = time.monotonic()
                if self._eyes is not None and now - patches_at >= self._params.patch_interval_sec:
                    patches_at = now
                    side = self._params.patch_pixels
                    frame['p'] = {
                        name: _encode_patch(patch, side) for name, patch in self._eyes().items()
                    }
                writer.write(b'data: ' + json.dumps(frame, separators=(',', ':')).encode('ascii') + b'\n\n')
                await writer.drain()
            await asyncio.sleep(interval)


def _query_int(path: str, key: str) -> int:
    values = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query).get(key, ['0'])
    try:
        return max(0, int(values[0]))
    except ValueError:
        return 0


def _load_page() -> bytes:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brain_view.html')
    with open(path, 'rb') as handle:
        return handle.read()
