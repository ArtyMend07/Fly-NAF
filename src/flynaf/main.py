import asyncio
import logging
import os

import torch

from flynaf import config, tuning
from flynaf.env.brain_view import SpikeFeed
from flynaf.env.cascade import CascadeTracer
from flynaf.env.frame_recorder import FrameRecorder, frames_folder
from flynaf.env.input_controller import FNAFController, start_worker
from flynaf.env.overlay import anchor_to_game, bring_game_forward
from flynaf.env.tablet_feed import TabletFeed
from flynaf.env.vision import FNAFVision
from flynaf.night.engine import ConnectomeEngine
from flynaf.night.hallway import build_eye
from flynaf.night.memory import Memories
from flynaf.night.panel import brain_view_task
from flynaf.night.state import SaccadeRequest, SensoryState
from flynaf.night.tablet.senses import TabletSenses
from flynaf.night.tablet.watch import TabletWatch, build_gaze
from flynaf.night.tasks import engine_task, saccade_task, vision_task
from flynaf.recorder import SessionRecorder
from flynaf.telemetry import ConnectomeTelemetry

_log = logging.getLogger(__name__)


async def _run(telemetry: ConnectomeTelemetry, trace: SessionRecorder, begin_night=None):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    _log.info('brain core online, device=%s', device)

    start_worker(bring_game_forward)
    engine = ConnectomeEngine(device)
    vision = FNAFVision()
    controller = FNAFController()
    state = SensoryState()
    shutdown = asyncio.Event()
    calibration_done = asyncio.Event()
    view_ready = asyncio.Event()
    tracer = CascadeTracer.from_csr(engine.synapses) if config.BRAIN_VIEW.enabled else None
    feed = SpikeFeed(engine.num_neurons, tracer)
    saccade = SaccadeRequest()
    tablet_feed = TabletFeed()
    memories = Memories()
    tablet = TabletWatch(build_gaze(), tablet_feed, controller, telemetry, state, memories)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(vision_task(
            vision, controller, state, shutdown, TabletSenses(tablet_feed), build_eye(),
        ))
        tg.create_task(saccade_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            saccade, view_ready, begin_night, tablet_feed,
        ))
        tg.create_task(engine_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            feed, saccade, trace, tablet, memories,
        ))
        tg.create_task(brain_view_task(
            feed, shutdown, view_ready, vision.latest_patches,
        ))


def main(begin_night=None, record_frames: bool = False):
    trace = SessionRecorder(enabled=os.environ.get('FLYNAF_RECORD', '1') != '0')
    tuning.load()
    if anchor_to_game():
        _log.info('screen targets follow the game window, no calibration needed')
    else:
        _log.warning(
            'the game window was not found, so the screen targets in config.py are used as '
            'measured, which assumes a 1280x720 window at the top left of the display'
        )
    telemetry = ConnectomeTelemetry()
    if record_frames:
        FrameRecorder(frames_folder(trace.path), telemetry.start_time).start()
    try:
        asyncio.run(_run(telemetry, trace, begin_night))
    except KeyboardInterrupt:
        _log.info('shutdown')
    finally:
        trace.close()
        path = telemetry.dump_report()
        _log.info('Telemetry report saved to %s', path)
