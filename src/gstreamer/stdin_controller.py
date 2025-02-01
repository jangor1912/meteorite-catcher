import asyncio
import logging
import random
import sys
import uuid
from functools import partial
from pathlib import Path
from typing import Callable
from src.gstreamer.pipeline import initialize_gstreamer, TrackerPipeline
import numpy as np

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')

from gi.repository import GLib, Gst

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()


async def connect_stdin_stdout():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    w_transport, w_protocol = await loop.connect_write_pipe(asyncio.streams.FlowControlMixin, sys.stdout)
    writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)
    return reader, writer


async def connect_stdin() -> asyncio.StreamReader:
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


async def switch_on_stdin(
        switch_state_func: Callable[[], None]
) -> None:
    async def _read_stdin() -> None:
        reader = await connect_stdin()
        while True:
            res = await reader.read(100)
            if not res:
                break
            else:
                switch_state_func()
            logger.info(res)
    my_task = asyncio.create_task(_read_stdin())
    try:
        await asyncio.wait_for(my_task, timeout=5)
    except asyncio.TimeoutError:
        logger.error("Unable to complete future within 10 ms")


async def wait_for_5_seconds() -> None:
    async def _wait_for_5_seconds() -> None:
        await asyncio.sleep(5)
    my_task = asyncio.create_task(_wait_for_5_seconds())
    try:
        await asyncio.wait_for(my_task, timeout=0.01)
    except asyncio.TimeoutError:
        logger.error("Unable to complete future within 3 seconds")


def normal_callback(pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
    unique_uuid = str(uuid.uuid4())
    logger.info(f"[{unique_uuid}] Reached normal callback!")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(wait_for_5_seconds())
    loop.close()
    del loop
    logger.info(f"[{unique_uuid}] Finished normal callback!")
    return Gst.PadProbeReturn.OK


def switch_state_callback(
        pad: Gst.Pad,
        info: Gst.PadProbeInfo,
        switch_state_func: Callable[[], None]
) -> Gst.PadProbeReturn:
    unique_uuid = str(uuid.uuid4())
    logger.info(f"[{unique_uuid}] Reached normal callback!")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(switch_on_stdin(switch_state_func))
    loop.close()
    del loop
    logger.info(f"[{unique_uuid}] Finished normal callback!")
    return Gst.PadProbeReturn.OK


def switch_on_random_callback(
        pad: Gst.Pad,
        info: Gst.PadProbeInfo,
        switch_state_func: Callable[[], None]
) -> Gst.PadProbeReturn:
    unique_uuid = str(uuid.uuid4())
    # logger.info(f"[{unique_uuid}] Reached 'switch_on_random_callback' callback!")

    random_int = random.randint(1, 100)
    if random_int <= 1:
        logger.info(f"[{unique_uuid}] Switching in 'switch_on_random_callback'!")
        switch_state_func()

    # logger.info(f"[{unique_uuid}] Finished 'switch_on_random_callback' callback!")
    return Gst.PadProbeReturn.OK


def compute_numpy_frame(frame: np.array) -> None:
    logger.info(f"Received new numpy frame with dimensions {frame.shape}")


if __name__ == "__main__":
    print("Starting the STDIN controller!")
    initialize_gstreamer()
    main_loop = GLib.MainLoop()

    local_rtsp_url = "rtsp://mediamtx:8554/mystream"
    logger.info(f"Creating TrackingPipeline for stream {local_rtsp_url}")
    pipeline = TrackerPipeline(
        camera_id="some-camera-id",
        rtsp_url=local_rtsp_url,
        recordings_directory=Path("/data/videos")
    )
    logger.info(f"Successfully created TrackingPipeline for stream {local_rtsp_url}")

    callback = partial(switch_on_random_callback, switch_state_func=pipeline.switch_state)

    pipeline.add_callback_probe(callback)

    pipeline.add_app_sink_new_sample_callback(compute_numpy_frame)

    pipeline.start_pipeline(main_loop)

    try:
        main_loop.run()
    except Exception as e:
        logger.error(f"Exception during pipeline execution. Error = {e}")
        pass

