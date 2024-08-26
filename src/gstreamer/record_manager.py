import collections
import logging
from dataclasses import dataclass, field
from typing import Callable

from src.gstreamer.utils import RecordingState

logger = logging.getLogger(__name__)


@dataclass
class RecordManager:
    start_recording_function: Callable[[], None]
    stop_recording_function: Callable[[], None]

    # number of frames with detections after which the manager will start recording
    start_recording_threshold: int = 5
    # number of frames without detections after which the manager will stop recording
    stop_recording_threshold: int = 10

    _state: RecordingState = field(default=RecordingState.NOT_STARTED, init=False)

    _last_30_frames: collections.deque = field(
        default_factory=lambda: collections.deque([False] * 30, maxlen=30),
        init=False
    )

    def update_frame(self, objects_detected: bool) -> None:
        self._last_30_frames.append(objects_detected)

        if self._state == RecordingState.NOT_STARTED:
            # check if the number of last consecutive detections are equal to `start_recording_threshold`
            should_start_recording = True
            for i in range(self.start_recording_threshold):
                if not self._last_30_frames[-i]:
                    should_start_recording = False
                    break

            if should_start_recording:
                self.start_recording()

        elif self._state == RecordingState.RECORDING:
            # check if the number of last consecutive non-detections are lesser than `stop_recording_threshold`
            should_stop_recording = True
            for i in range(self.stop_recording_threshold):
                if self._last_30_frames[-i]:
                    should_stop_recording = False
                    break

            if should_stop_recording:
                self.stop_recording()

    def start_recording(self) -> None:
        logger.info("Starting recording.")
        try:
            self._state = self._state.next_state()  # STARTING
            self.start_recording_function()
            self._state = self._state.next_state()  # RECORDING
            logger.info("Successfully started recording.")
        except Exception as e:
            logger.error(f"Error during starting recording: {e}")
            self._state = RecordingState.NOT_STARTED

    def stop_recording(self) -> None:
        logger.info("Stopping recording.")
        try:
            self._state = self._state.next_state()  # STOPPING
            self.stop_recording_function()
            self._state = self._state.next_state()  # STOPPED
            self._state = self._state.next_state()  # NOT_STARTED
            logger.info("Successfully stopped recording.")
        except Exception as e:
            logger.error(f"Error during stopping recording: {e}")
            self._state = RecordingState.RECORDING
