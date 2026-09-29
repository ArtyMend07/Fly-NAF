import collections

import numpy as np


class CascadeTracer:
    def __init__(
        self,
        crow: np.ndarray,
        col: np.ndarray,
        weight: np.ndarray,
        history: int = 16,
        fan_in: int = 3,
        edge_cap: int = 160,
    ):
        self._crow = crow
        self._col = col
        self._weight = weight
        self._frames = collections.deque(maxlen=history)
        self._fan_in = fan_in
        self._edge_cap = edge_cap

    @classmethod
    def from_csr(cls, matrix, **limits):
        matrix = matrix.to('cpu')
        return cls(
            matrix.crow_indices().numpy().astype(np.int64, copy=False),
            matrix.col_indices().numpy().astype(np.int32),
            matrix.values().numpy().astype(np.float32, copy=False),
            **limits,
        )

    def record(self, spiking: np.ndarray):
        fired = np.zeros(len(self._crow) - 1, dtype=bool)
        fired[np.asarray(spiking, dtype=np.int64)] = True
        self._frames.append(fired)

    def _inputs_fired(self, post: int, fired: np.ndarray):
        start, end = self._crow[post], self._crow[post + 1]
        pre = self._col[start:end]
        weight = self._weight[start:end]
        hit = fired[pre]
        return pre[hit], weight[hit]

    def trace(self, target: int, sources=()) -> dict:
        frames = list(self._frames)
        newest = len(frames) - 1
        sources = set(int(s) for s in sources)
        edges = []
        inhibitory = 0
        reached_source = None
        visited = {int(target)}
        frontier = [(int(target), newest, False)]

        while frontier and len(edges) < self._edge_cap:
            following = []
            for post, at, arrived_in_frame in frontier:
                candidates = []
                for fired_at in (at - 1, at) if not arrived_in_frame else (at - 1,):
                    if fired_at < 0:
                        continue
                    pre, weight = self._inputs_fired(post, frames[fired_at])
                    inhibitory += int((weight < 0).sum())
                    for p, w in zip(pre.tolist(), weight.tolist()):
                        if w > 0 and p not in visited:
                            candidates.append((w, p, fired_at))
                candidates.sort(reverse=True)
                for w, p, fired_at in candidates[:self._fan_in]:
                    if p in visited:
                        continue
                    visited.add(p)
                    edges.append((p, post, newest - fired_at, newest - at, w))
                    if p in sources:
                        age = newest - fired_at
                        reached_source = age if reached_source is None else max(reached_source, age)
                    following.append((p, fired_at, fired_at == at))
                    if len(edges) >= self._edge_cap:
                        break
                if len(edges) >= self._edge_cap:
                    break
            frontier = following

        depth = max((edge[2] for edge in edges), default=0)
        return {
            'target': int(target),
            'edges': [[int(p), int(q), int(a), int(b), round(float(w), 3)] for p, q, a, b, w in edges],
            'depth': int(depth),
            'reached_source': reached_source,
            'inhibitory_inputs': inhibitory,
        }
