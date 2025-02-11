import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from ioutrack import Sort

from src.detectors.frame_diff import FrameDiffDetector
from src.file_operations.writer import ImageWriter
from src.gstreamer.pipeline import initialize_gstreamer, TrackerPipeline

import gi

from src.gstreamer.record_manager import RecordManager
from src.gstreamer.utils import RecordingState
from src.inference.base import BaseInferenceEngine
from src.inference.inference import FrameDiffInference

gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')

from gi.repository import GLib, Gst

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()


@dataclass
class DetectorController:
    pipeline: TrackerPipeline
    inference_engine: BaseInferenceEngine
    image_output_directory: Path | None = None
    record_manager: RecordManager | None = field(init=False, default=None)
    _last_state_log_datetime: datetime = field(init=False, default_factory=datetime.now)

    inference_frame_num: int = 0
    app_tee_frame_num: int = 0

    def __post_init__(self):
        image_writer = None
        if self.image_output_directory is not None:
            image_writer = ImageWriter(
                output_directory=self.image_output_directory,
                quick=False
            )
        self.record_manager = RecordManager(
            start_recording_function=self.on_start_recording,
            stop_recording_function=self.on_stop_recording,
            get_state_function=self.get_pipeline_state,
            image_writer=image_writer,
            start_recording_threshold=2,
        )

    def get_pipeline_state(self) -> RecordingState:
        return self.pipeline.state

    def switch_on_record_manager_callback(
            self,
            pad: Gst.Pad,
            info: Gst.PadProbeInfo
    ) -> Gst.PadProbeReturn:
        self.app_tee_frame_num += 1
        current_time = datetime.now()
        if current_time - self._last_state_log_datetime > timedelta(seconds=3):
            logger.info(f"State of the pipeline is {self.get_pipeline_state().value}")
            logger.info(f"Decoded and processed frames: {self.inference_frame_num}")
            logger.info(f"Depayed frames: {self.pipeline.frames_consumed}")
            logger.info(f"Diff: {self.pipeline.frames_consumed - self.inference_frame_num}")
            self._last_state_log_datetime = current_time
        return Gst.PadProbeReturn.OK

    def update_with_frame(self, frame: np.array) -> None:
        # logger.info(f"Received new numpy frame with dimensions {frame.shape}")
        bboxes = self.inference_engine.update(frame)
        self.record_manager.update_frame(frame, bboxes)
        self.inference_frame_num += 1

    def on_start_recording(self) -> None:
        logger.info("Recording should start now!")
        self.pipeline.begin_starting_recording()

    def on_stop_recording(self) -> None:
        logger.info("Recording should stop now!")
        self.pipeline.begin_stopping_recording()


def main() -> None:
    print("Starting the meteorite-detector controller!")
    initialize_gstreamer()
    main_loop = GLib.MainLoop()

    local_rtsp_url = "rtsp://mediamtx:8554/mystream"

    logger.info(f"Creating TrackingPipeline for stream {local_rtsp_url}")
    pipeline = TrackerPipeline(
        camera_id="some-camera-id",
        rtsp_url=local_rtsp_url,
        recordings_directory=Path("/data/videos"),
        recording_buffer=int(3e9)
    )
    logger.info(f"Successfully created TrackingPipeline for stream {local_rtsp_url}")

    inference_engine = FrameDiffInference(
        detector=FrameDiffDetector(bbox_threshold=128, nms_threshold=1e-3),
        tracker=Sort(min_hits=3, max_age=5)
    )

    controller = DetectorController(
        inference_engine=inference_engine,
        pipeline=pipeline,
        image_output_directory=Path("/data/videos"),
    )

    pipeline.add_callback_probe(controller.switch_on_record_manager_callback)

    pipeline.add_app_sink_new_sample_callback(controller.update_with_frame)

    pipeline.start_pipeline(main_loop)

    try:
        main_loop.run()
    except Exception as e:
        logger.error(f"Exception during pipeline execution. Error = {e}")
        pass


if __name__ == "__main__":
    main()
