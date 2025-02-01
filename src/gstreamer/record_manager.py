import collections
import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from src.file_operations.images import draw_tracks_numpy
from src.file_operations.writer import ImageWriter
from src.gstreamer.utils import RecordingState
from src.types import BBoxList

logger = logging.getLogger(__name__)


@dataclass
class RecordManager:
    start_recording_function: Callable[[], None]
    stop_recording_function: Callable[[], None]
    get_state_function: Callable[[], RecordingState]
    image_writer: ImageWriter | None = None

    # number of frames with detections after which the manager will start recording
    start_recording_threshold: int = 5
    # number of frames without detections after which the manager will stop recording
    stop_recording_threshold: int = 10

    _last_30_frames: collections.deque = field(
        default_factory=lambda: collections.deque([False] * 30, maxlen=30),
        init=False
    )

    def update_frame(self, frame: np.array, bboxes: BBoxList) -> None:
        objects_detected = bboxes.size != 0
        self._last_30_frames.append(objects_detected)
        state = self.get_state_function()

        if state == RecordingState.NOT_STARTED or state == RecordingState.STOPPED:
            # check if the number of last consecutive detections are equal to `start_recording_threshold`
            should_start_recording = True
            for i in range(self.start_recording_threshold):
                if not self._last_30_frames[-i]:
                    should_start_recording = False
                    break

            if should_start_recording:
                self.save_preview_image(frame, bboxes)
                self.start_recording_function()

        elif state == RecordingState.RECORDING:
            # check if the number of last consecutive non-detections are lesser than `stop_recording_threshold`
            should_stop_recording = True
            for i in range(self.stop_recording_threshold):
                if self._last_30_frames[-i]:
                    should_stop_recording = False
                    break

            if should_stop_recording:
                self.stop_recording_function()

    def save_preview_image(self, frame: np.array, bboxes: BBoxList) -> None:
        if self.image_writer is None:
            return

        painted_frame = draw_tracks_numpy(frame, bboxes)
        self.image_writer.save(painted_frame)
