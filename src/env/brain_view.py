import asyncio
import base64
import csv
import os
import struct

import numpy as np

import config

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


class SpikeFeed:
    def __init__(self, num_neurons: int = 0):
        self.indices = np.empty(0, dtype=np.uint32)
        self._seen = np.zeros(num_neurons, dtype=bool)
        self.fired_total = 0
        self.spike_total = 0
        self.revision = 0

    def publish(self, spiking: np.ndarray):
        self.indices = np.unique(spiking).astype(np.uint32, copy=False)
        self.spike_total += int(self.indices.size)
        if self._seen.size:
            fresh = ~self._seen[self.indices]
            self.fired_total += int(fresh.sum())
            self._seen[self.indices] = True
        self.revision += 1


def _read_soma_positions() -> np.ndarray:
    path = os.path.join(config.DATA_DIR, 'soma_coordinates_783.csv')
    with open(path, newline='') as handle:
        rows = list(csv.reader(handle))
    coords = np.array([[float(r[1]), float(r[2]), float(r[3])] for r in rows[1:]], dtype=np.float32)
    center = (coords.max(axis=0) + coords.min(axis=0)) / 2.0
    coords -= center
    scale = float(np.abs(coords).max())
    if scale > 0:
        coords /= scale
    coords[:, 1] *= -1.0
    return coords


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


def build_geometry_blob() -> bytes:
    positions = _read_soma_positions()
    regions = _read_regions(_read_root_ids())
    count = min(len(positions), len(regions))
    header = struct.pack('<I', count)
    return header + positions[:count].tobytes() + regions[:count].tobytes()


class BrainViewServer:
    def __init__(self, feed: SpikeFeed, highlights: dict):
        self._feed = feed
        self._highlights = highlights
        self._geometry = None
        self._page = None
        self._server = None
        self._params = config.BRAIN_VIEW

    async def start(self) -> int:
        loop = asyncio.get_event_loop()
        self._geometry = await loop.run_in_executor(None, build_geometry_blob)
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
            elif path.startswith('/stream'):
                await self._stream(writer)
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
        interval = self._params.stream_interval_sec
        while not writer.is_closing():
            feed = self._feed
            if feed.revision != sent:
                sent = feed.revision
                payload = base64.b64encode(feed.indices.tobytes()).decode('ascii')
                meta = self._highlights
                frame = (
                    '{"s":"' + payload + '"'
                    + ',"fired":' + str(feed.fired_total)
                    + ',"spikes":' + str(feed.spike_total)
                    + ',"gaze":"' + str(meta.get('gaze', '--')) + '"'
                    + ',"gf_l":' + ('true' if meta.get('gf_l') else 'false')
                    + ',"gf_r":' + ('true' if meta.get('gf_r') else 'false')
                    + ',"camera":' + ('true' if meta.get('camera') else 'false')
                    + '}'
                )
                writer.write(b'data: ' + frame.encode('ascii') + b'\n\n')
                await writer.drain()
            await asyncio.sleep(interval)


def _load_page() -> bytes:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brain_view.html')
    with open(path, 'rb') as handle:
        return handle.read()
