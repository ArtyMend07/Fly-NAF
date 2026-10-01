import asyncio
import logging
import os

import torch

import config
from env.brain_view import SpikeFeed
from env.cascade import CascadeTracer
from env.input_controller import FNAFController, start_worker
from env.overlay import anchor_to_game
from env.tablet_feed import TabletFeed
from env.vision import FNAFVision
from night.engine import ConnectomeEngine
from night.panel import brain_view_task
from night.state import SaccadeRequest, SensoryState
from night.tablet.senses import TabletSenses
from night.tablet.watch import TabletWatch, build_gaze
from night.tasks import engine_task, saccade_task, vision_task
from recorder import SessionRecorder
from telemetry import ConnectomeTelemetry
import tuning

_log = logging.getLogger(__name__)


async def _run(telemetry: ConnectomeTelemetry, trace: SessionRecorder, begin_night=None):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    _log.info('brain core online, device=%s', device)

    start_worker()
    engine = ConnectomeEngine(device)
    vision = FNAFVision()
    controller = FNAFController()
    state = SensoryState()
    shutdown = asyncio.Event()
    calibration_done = asyncio.Event()
    view_ready = asyncio.Event()
    tracer = CascadeTracer.from_csr(engine.synapses) if config.BRAIN_VIEW.enabled else None
    feed = SpikeFeed(engine.num_neurons, tracer)
    highlights = {'gaze': '--', 'gf_l': False, 'gf_r': False, 'camera': False}
    saccade = SaccadeRequest()
    tablet_feed = TabletFeed()
    tablet = TabletWatch(build_gaze(), tablet_feed, controller, telemetry, state)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(vision_task(
            vision, controller, state, shutdown, TabletSenses(tablet_feed),
        ))
        tg.create_task(saccade_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            saccade, view_ready, begin_night, tablet_feed,
        ))
        tg.create_task(engine_task(
            engine, vision, controller, state, shutdown, telemetry, calibration_done,
            feed, highlights, saccade, trace, tablet,
        ))
        tg.create_task(brain_view_task(
            feed, highlights, shutdown, view_ready, vision.latest_patches,
        ))


def main(begin_night=None):
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
    try:
        asyncio.run(_run(telemetry, trace, begin_night))
    except KeyboardInterrupt:
        _log.info('shutdown')
    finally:
        trace.close()
        path = telemetry.dump_report()
        _log.info('Telemetry report saved to %s', path)
