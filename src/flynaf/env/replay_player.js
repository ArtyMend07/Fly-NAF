(() => {
  const SOURCES = {
    neurons: 'https://raw.githubusercontent.com/eonsystemspbc/fly-brain/a3db62f9436074e485c0278290c2164ed6150808/data/2025_Completeness_783.csv',
    annotations: 'https://raw.githubusercontent.com/flyconnectome/flywire_annotations/8587524c1748ce5ef2080822a2fc890fc03bf597/supplemental_files/Supplemental_file1_neuron_annotations.tsv',
    outline: 'https://raw.githubusercontent.com/navis-org/navis-flybrains/273333c8d8bf5adeebebd274e554621462e388bd/flybrains/meshes/FLYWIRE.ply',
  };
  const REGION = {
    optic: 0, visual_centrifugal: 0, central: 1, endocrine: 1, sensory: 2, sensory_ascending: 2,
    visual_projection: 2, ascending: 2, descending: 3, motor: 3,
  };
  const VOXEL_NM = [4, 4, 40];
  const SPEEDS = [1, 2, 4, 8];

  const fetched = (url, read) => fetch(url).then(response => {
    if (!response.ok) throw new Error(`${response.status} for ${url}`);
    return read(response);
  });

  function parseMesh(buffer) {
    const head = new TextDecoder('ascii').decode(new Uint8Array(buffer, 0, Math.min(buffer.byteLength, 4096)));
    const marker = 'end_header\n';
    const start = head.indexOf(marker) + marker.length;
    const vertexCount = Number(head.match(/element vertex (\d+)/)[1]);
    const faceCount = Number(head.match(/element face (\d+)/)[1]);
    const view = new DataView(buffer, start);
    const vertices = new Float32Array(vertexCount * 3);
    for (let i = 0; i < vertices.length; i++) vertices[i] = view.getFloat32(i * 4, true);
    const faces = new Uint32Array(faceCount * 3);
    const faceStart = vertexCount * 12;
    for (let f = 0; f < faceCount; f++) {
      for (let j = 0; j < 3; j++) faces[f * 3 + j] = view.getUint32(faceStart + f * 13 + 1 + j * 4, true);
    }
    return { vertices, faces };
  }

  function percentile(sorted, q) {
    const at = (sorted.length - 1) * q;
    const low = Math.floor(at);
    const high = Math.min(low + 1, sorted.length - 1);
    return sorted[low] + (sorted[high] - sorted[low]) * (at - low);
  }

  function placer(vertices) {
    const center = [], spans = [];
    for (let axis = 0; axis < 3; axis++) {
      const values = Float32Array.from({ length: vertices.length / 3 }, (_, i) => vertices[i * 3 + axis]).sort();
      const low = percentile(values, 0.005);
      const high = percentile(values, 0.995);
      center.push((low + high) / 2);
      spans.push(high - low);
    }
    const scale = Math.max(...spans) / 2 || 1;
    return (out, at, x, y, z) => {
      out[at] = (x - center[0]) / scale;
      out[at + 1] = -(y - center[1]) / scale;
      out[at + 2] = -(z - center[2]) / scale;
    };
  }

  function neuronOrder(csv) {
    return csv.split('\n').slice(1).map(line => line.slice(0, line.indexOf(','))).filter(Boolean);
  }

  function annotationsByRoot(tsv) {
    const lines = tsv.split('\n');
    const header = lines[0].split('\t');
    const col = name => header.indexOf(name);
    const [root, x, y, z, superClass] = ['root_id', 'pos_x', 'pos_y', 'pos_z', 'super_class'].map(col);
    const byRoot = new Map();
    for (let i = 1; i < lines.length; i++) {
      const cells = lines[i].split('\t');
      if (cells.length <= superClass) continue;
      byRoot.set(cells[root], [Number(cells[x]), Number(cells[y]), Number(cells[z]), REGION[cells[superClass]] ?? 1]);
    }
    return byRoot;
  }

  function geometryBuffer(order, byRoot, place) {
    const buffer = new ArrayBuffer(4 + order.length * 13);
    new DataView(buffer).setUint32(0, order.length, true);
    const positions = new Float32Array(buffer, 4, order.length * 3);
    const regions = new Uint8Array(buffer, 4 + order.length * 12, order.length);
    order.forEach((rootId, i) => {
      const found = byRoot.get(rootId);
      regions[i] = found ? found[3] : 1;
      if (found) place(positions, i * 3, found[0] * VOXEL_NM[0], found[1] * VOXEL_NM[1], found[2] * VOXEL_NM[2]);
    });
    return buffer;
  }

  function outlineBuffer(mesh, place) {
    const vertexCount = mesh.vertices.length / 3;
    const buffer = new ArrayBuffer(8 + mesh.vertices.length * 4 + mesh.faces.length * 4);
    new Uint32Array(buffer, 0, 2).set([vertexCount, mesh.faces.length / 3]);
    const placed = new Float32Array(buffer, 8, mesh.vertices.length);
    for (let i = 0; i < vertexCount; i++) {
      place(placed, i * 3, mesh.vertices[i * 3], mesh.vertices[i * 3 + 1], mesh.vertices[i * 3 + 2]);
    }
    new Uint32Array(buffer, 8 + mesh.vertices.length * 4, mesh.faces.length).set(mesh.faces);
    return buffer;
  }

  function decodeSpikes(buffer) {
    const bytes = new Uint8Array(buffer);
    let at = 0;
    const read = () => {
      let value = 0, scale = 1, byte;
      do {
        byte = bytes[at++];
        value += (byte & 0x7f) * scale;
        scale *= 128;
      } while (byte & 0x80);
      return value;
    };
    const frames = new Array(read());
    for (let f = 0; f < frames.length; f++) {
      const indices = new Uint32Array(read());
      let previous = 0;
      for (let i = 0; i < indices.length; i++) indices[i] = previous += read();
      frames[f] = indices;
    }
    return frames;
  }

  function prepareNight(night, spikes) {
    const seen = new Uint8Array(200000);
    let fired = 0, total = 0;
    const cascades = new Map(night.cascades.map(c => [c.frame - 1, c]));
    return night.rows.map((row, f) => {
      const frame = Object.fromEntries(night.keys.map((key, k) => [key, row[k]]));
      for (const index of spikes[f]) if (!seen[index]) { seen[index] = 1; fired++; }
      total += spikes[f].length;
      Object.assign(frame, {
        indices: spikes[f], fired, spikes: total, ms: night.ms_per_frame,
        mse_th: night.settings.mse_threshold, look_l: frame.in_l, look_r: frame.in_r,
        gaze: frame.in_l ? 'LEFT' : frame.in_r ? 'RIGHT' : '--',
      });
      if (cascades.has(f)) frame.c = cascades.get(f);
      return frame;
    });
  }

  const status = text => {
    const state = document.getElementById('state');
    if (state) state.textContent = text;
  };

  const world = (() => {
    let resolved = null;
    return () => resolved ??= Promise.all([
      fetched(SOURCES.outline, r => r.arrayBuffer()).then(parseMesh),
      fetched(SOURCES.neurons, r => r.text()).then(neuronOrder),
      fetched(SOURCES.annotations, r => r.text()).then(annotationsByRoot),
    ]).then(([mesh, order, byRoot]) => {
      const place = placer(mesh.vertices);
      return { geometry: geometryBuffer(order, byRoot, place), outline: outlineBuffer(mesh, place) };
    });
  })();

  const recording = Promise.all([
    fetched('night.json', r => r.json()),
    fetched('spikes.bin', downloadWithProgress).then(decodeSpikes),
  ]).then(([night, spikes]) => ({ night, frames: prepareNight(night, spikes) }));

  async function downloadWithProgress(response) {
    const total = Number(response.headers.get('content-length')) || 0;
    const reader = response.body.getReader();
    const parts = [];
    let received = 0;
    for (let chunk = await reader.read(); !chunk.done; chunk = await reader.read()) {
      parts.push(chunk.value);
      received += chunk.value.length;
      if (total) status(`LOADING THE NIGHT ${Math.round(received / total * 100)}%`);
    }
    const bytes = new Uint8Array(received);
    let at = 0;
    for (const part of parts) { bytes.set(part, at); at += part.length; }
    return bytes.buffer;
  }

  const clockText = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;

  function controls(night, frames, onFrame) {
    const first = frames[0].t, last = frames[frames.length - 1].t;
    const bar = document.getElementById('player');
    const play = bar.querySelector('#play'), seek = bar.querySelector('#seek');
    const speed = bar.querySelector('#speed'), shown = bar.querySelector('#elapsed');
    let next = 0, position = first, playing = true, previous = performance.now();
    seek.max = String(last - first);
    const jump = to => {
      position = Math.max(first, Math.min(last, to));
      next = frames.findIndex(frame => frame.t >= position);
      if (next < 0) next = frames.length;
    };
    play.onclick = () => { playing = !playing; play.textContent = playing ? 'PAUSE' : 'PLAY'; };
    seek.oninput = () => jump(first + Number(seek.value));
    const tick = now => {
      const elapsed = Math.max(0, Math.min(0.25, (now - previous) / 1000));
      previous = now;
      if (playing) position += elapsed * SPEEDS[speed.selectedIndex];
      while (playing && next < frames.length && frames[next].t <= position) onFrame(frames[next++]);
      if (next >= frames.length) { jump(first); }
      seek.value = String(position - first);
      shown.textContent = `${clockText(position - first)} / ${clockText(last - first)}`;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function dropUnrecordedDoors(night) {
    const door = night.keys.indexOf('door_l');
    if (night.rows.some(row => row[door] != null)) return;
    for (let i = ROWS.length - 1; i >= 0; i--) if (ROWS[i].kind === 'door') ROWS.splice(i, 1);
    FIRST_ROW.right = ROWS.findIndex(row => row.kind === 'stim' && row.side === 'r');
  }

  function dress(night) {
    document.querySelector('h1').textContent = 'FLY CONNECTOME · NIGHT 3 REPLAY';
    dropUnrecordedDoors(night);
    const recorded = night.recorded_at.slice(0, 10);
    document.getElementById('about-when').textContent =
      `recorded on ${recorded}, replayed through the current brain on ${night.replayed_on}`;
  }

  function addControls() {
    const style = document.createElement('style');
    style.textContent = `
      #player { display: flex; gap: 8px; align-items: center; padding: 7px 12px; border-top: 1px solid var(--line);
        font-size: 9.5px; letter-spacing: 0.08em; color: var(--label); }
      #player button, #player select { font: inherit; color: var(--value); background: var(--well);
        border: 1px solid var(--line); border-radius: 999px; padding: 3px 10px; cursor: pointer; }
      #player input { flex: 1; min-width: 60px; accent-color: var(--light); }
      #about { padding: 8px 12px 10px; border-top: 1px solid var(--line); font-size: 9px; line-height: 1.6;
        color: var(--label); max-height: 32vh; overflow-y: auto; }
      #about[hidden] { display: none; }
      #about a { color: var(--value); }
      #about p + p { margin-top: 6px; }`;
    document.head.appendChild(style);
    document.body.insertAdjacentHTML('beforeend', `
      <div id="player"><button id="play">PAUSE</button><input id="seek" type="range" min="0" step="0.1" value="0">
        <span id="elapsed">0:00</span><select id="speed">${SPEEDS.map(s => `<option>${s}×</option>`).join('')}</select>
        <button id="about-toggle">ABOUT</button></div>
      <div id="about" hidden>
        <p>A fruit fly brain played night 3 of Five Nights at Freddy's and reached 5 AM. What its eyes and the tablet
        fed into the brain was written down every frame, and here that input runs again through the 138,639 neurons
        of the FlyWire 783 connectome. Every dot is a neuron, lit when it fires. The spikes were computed beforehand
        with <code>run.py --replay</code>, <span id="about-when"></span>. Your browser only plays them back.</p>
        <p>Nothing from the game is on this page or needed by it. The recording holds numbers only: how far each
        hallway was from its empty view, which camera was up and how strongly a figure on it drove the brain. Five
        Nights at Freddy's is a game by Scott Cawthon, and this project is not affiliated with or endorsed by him.
        Playing a night live needs your own copy of the game.</p>
        <p>Neuron positions and classes load from <a href="https://github.com/flyconnectome/flywire_annotations">flywire_annotations</a>
        (Dorkenwald et al. 2024, Schlegel et al. 2024, Matsliah et al. 2024, Berg et al. 2025), the neuron order from
        <a href="https://github.com/eonsystemspbc/fly-brain">eonsystemspbc/fly-brain</a> and the brain outline from
        <a href="https://github.com/navis-org/navis-flybrains">navis-flybrains</a>, straight from those repositories.
        FlyWire data is released under CC BY-NC 4.0. Code and write-up at
        <a href="https://github.com/ArtyMend07/Fly-NAF">github.com/ArtyMend07/Fly-NAF</a>.</p>
      </div>`);
    document.getElementById('about-toggle').onclick = () => {
      const about = document.getElementById('about');
      about.hidden = !about.hidden;
      window.dispatchEvent(new Event('resize'));
    };
  }

  window.flynafSource = {
    geometry: () => {
      status('LOADING 138,639 NEURONS');
      return world().then(loaded => loaded.geometry).catch(error => {
        status('COULD NOT LOAD THE NEURONS');
        throw error;
      });
    },
    outline: () => world().then(loaded => loaded.outline),
    connect: (onFrame, onLost) => {
      status('LOADING THE NIGHT');
      recording.then(({ night, frames }) => {
        dress(night);
        controls(night, frames, onFrame);
      }).catch(onLost);
    },
  };

  document.addEventListener('DOMContentLoaded', addControls);
})();
