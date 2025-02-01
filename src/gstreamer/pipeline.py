import datetime
import logging
import os
import sys
import time
from pathlib import Path
from typing import Callable

import gi
import numpy as np

from src.gstreamer.utils import RecordingState

gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstBase', '1.0')

gi.require_version('Gtk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')

from gi.repository import GLib, Gst, GObject


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()


def initialize_gstreamer() -> None:
    Gst.init(None)


class TrackerPipeline:
    """
    Pipeline for detecting meteorites and saving them to mp4 files

    rtsp_source -> rtp_queue -> depay -> h264parser \
    -> app_tee -> avdec_h264 -> videoconvert -> appsink
               -> queue -> sink_tee -> file_sink_queue -> mp4mux -> file_sink
                                    -> fakesink


    AppSink will emit signals to switch between `file_sink` and `fake_sink` routes.
    Due to queue with buffer after `app_tee` two things will happen:
    1. Recording will be started before the meteorite is detected.
    2. Recording will be stopped after the meteorite is no longer visible.

    """
    def __init__(self, camera_id: str, rtsp_url: str, recordings_directory: Path, recording_buffer: int = 5000000000):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self._recordings_directory = recordings_directory
        self._recording_buffer = recording_buffer
        self.frames_consumed = 0
        self.stop_recording_time = datetime.datetime.now()

        self.pipeline = Gst.Pipeline.new(f"camera-{self.camera_id}")

        self._rtsp_source = None
        self._rtp_queue = None
        self._depay = None
        self._parser = None

        self._app_tee = None

        # Decode video and pass frames to Meteorite Detector
        self._app_queue = None
        self._decoder = None
        self._videoconvert = None
        self._capsfilter = None
        self._appsink = None

        self._sink_queue = None
        self._sink_tee = None

        self._sink_tee_src_record_pad = None

        self._file_sink_queue = None
        self._mp4mux = None
        self._file_sink = None

        self._fake_sink_queue = None
        self._fake_sink = None

        self._recording_started_time = None
        self._recordings_directory.mkdir(parents=True, exist_ok=True)
        self.initialize_pipeline()

        self._state: RecordingState = RecordingState.NOT_STARTED
        self.recordings_counter = 0
        self._last_recording_start_time = time.time()
        self._last_recording_stop_time = time.time()

        self._new_sample_callbacks: list[Callable[[np.array], None]] = list()

    def initialize_pipeline(self) -> None:
        self._rtsp_source = Gst.ElementFactory.make("rtspsrc", "rtsp-source")
        self._rtp_queue = Gst.ElementFactory.make("queue", "rtp-queue")
        self._depay = Gst.ElementFactory.make("rtph264depay", "rtph264-depay")
        self._parser = Gst.ElementFactory.make("h264parse", "h264-parser")

        self._app_tee = Gst.ElementFactory.make("tee", "app-tee")

        self._app_queue = Gst.ElementFactory.make("queue", "app-queue")
        self._decoder = Gst.ElementFactory.make("decodebin3", "decoder")
        self._videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")
        self._capsfilter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        self._appsink = Gst.ElementFactory.make("appsink", "appsink")

        self._sink_queue = Gst.ElementFactory.make("queue", "sink-queue")
        self._sink_tee = Gst.ElementFactory.make("tee", "sink-tee")

        self._file_sink_queue = Gst.ElementFactory.make("queue", "file-sink-queue")
        self._mp4mux = Gst.ElementFactory.make("mp4mux", "mp4-muxer")
        self._file_sink = Gst.ElementFactory.make("filesink", "file-sink")

        self._fake_sink_queue = Gst.ElementFactory.make("queue", "fake-sink-queue")
        self._fake_sink = Gst.ElementFactory.make("fakesink", "fake-sink")

        assert self._rtsp_source
        assert self._rtp_queue
        assert self._depay
        assert self._parser
        assert self._app_tee
        assert self._app_queue
        assert self._decoder
        assert self._videoconvert
        assert self._capsfilter
        assert self._appsink
        assert self._sink_queue
        assert self._sink_tee
        assert self._file_sink_queue
        assert self._mp4mux
        assert self._file_sink
        assert self._fake_sink_queue
        assert self._fake_sink

        # Set caps for app-sink
        caps = Gst.Caps.from_string("video/x-raw, format=BGR")
        self._capsfilter.set_property("caps", caps)

        self.pipeline.add(self._rtsp_source)
        self.pipeline.add(self._rtp_queue)
        self.pipeline.add(self._depay)
        self.pipeline.add(self._parser)
        self.pipeline.add(self._app_tee)

        # Add app-sink branch
        # FIXME it fails on adding those elements to pipeline
        self.pipeline.add(self._app_queue)
        self.pipeline.add(self._decoder)
        self.pipeline.add(self._videoconvert)
        self.pipeline.add(self._capsfilter)
        self.pipeline.add(self._appsink)

        # Add file-sink branch
        self.pipeline.add(self._sink_queue)
        self.pipeline.add(self._sink_tee)
        self.pipeline.add(self._file_sink_queue)
        self.pipeline.add(self._mp4mux)
        self.pipeline.add(self._file_sink)
        self.pipeline.add(self._fake_sink_queue)
        self.pipeline.add(self._fake_sink)

        self._rtsp_source.connect("pad-added", self.on_rtsp_src_pad_added)

        assert self._rtp_queue.link(self._depay)
        assert self._depay.link(self._parser)
        assert self._parser.link(self._app_tee)

        # Link sink-queue
        app_tee_src_pad_0 = self._app_tee.get_request_pad("src_0")
        assert app_tee_src_pad_0
        sink_queue_sink_pad = self._sink_queue.get_static_pad("sink")
        assert sink_queue_sink_pad
        assert app_tee_src_pad_0.link(sink_queue_sink_pad) == Gst.PadLinkReturn.OK

        # Link app-sink branch
        app_tee_src_pad_1 = self._app_tee.get_request_pad("src_1")
        assert app_tee_src_pad_1
        app_queue_sink_pad = self._app_queue.get_static_pad("sink")
        assert app_queue_sink_pad
        assert app_tee_src_pad_1.link(app_queue_sink_pad) == Gst.PadLinkReturn.OK
        assert self._app_queue.link(self._decoder)
        # assert self._decoder.link(self._videoconvert)
        # decoder_src_pad_0 = self._decoder.get_request_pad("src_0")
        # assert decoder_src_pad_0
        # videoconvert_sink_pad = self._videoconvert.get_static_pad("sink")
        # assert videoconvert_sink_pad
        # assert decoder_src_pad_0.link(videoconvert_sink_pad) == Gst.PadLinkReturn.OK
        self._decoder.connect("pad-added", self.on_decoder_pad_added, None)
        assert self._videoconvert.link(self._capsfilter)
        assert self._capsfilter.link(self._appsink)

        self._sink_queue.link(self._sink_tee)

        sink_tee_src_pad_0 = self._sink_tee.get_request_pad("src_0")
        assert sink_tee_src_pad_0
        fake_sink_queue_sink_pad = self._fake_sink_queue.get_static_pad("sink")
        assert fake_sink_queue_sink_pad
        assert sink_tee_src_pad_0.link(fake_sink_queue_sink_pad) == Gst.PadLinkReturn.OK
        assert self._fake_sink_queue.link(self._fake_sink)

        sink_tee_src_pad_1 = self._sink_tee.get_request_pad("src_1")
        self._sink_tee_src_record_pad = sink_tee_src_pad_1

        assert self._sink_tee_src_record_pad
        file_sink_queue_sink_pad = self._file_sink_queue.get_static_pad("sink")
        assert file_sink_queue_sink_pad
        assert self._sink_tee_src_record_pad.link(file_sink_queue_sink_pad) == Gst.PadLinkReturn.OK
        assert self._file_sink_queue.link(self._mp4mux)
        assert self._mp4mux.link(self._file_sink)

        # add probe to fake-sink queue
        sink_queue_src_pad = self._sink_queue.get_static_pad("src")
        assert sink_queue_src_pad
        sink_queue_src_pad.add_probe(Gst.PadProbeType.BUFFER, self._sink_queue_probe_callback)

        # set rtsp url
        self._rtsp_source.set_property("location", self.rtsp_url)

        # set file sink location
        self._file_sink.set_property(
            "location",
            f"{self._recordings_directory}/first-few-frames.mp4"
        )

        # set buffer on file-sink queue to record some time before transaction
        self._sink_queue.set_property("min-threshold-time", self._recording_buffer)
        self._sink_queue.set_property("max-size-buffers", 0)
        self._sink_queue.set_property("max-size-time", 0)
        self._sink_queue.set_property("max-size-bytes", 0)

        # add callbacks to app-sink
        self._appsink.set_property("emit-signals", True)
        self._appsink.set_property("sync", False)  # Set sync=False to process frames as fast as they arrive.
        self._appsink.connect("new-sample", self._on_new_sample, None)

    @property
    def state(self) -> RecordingState:
        return self._state

    @state.setter
    def state(self, new_state: RecordingState) -> None:
        logger.info(f"Changing state from {self._state.value} to {new_state.value}")
        self._state = new_state

    def add_bus_to_pipeline(self, loop: GLib.MainLoop) -> None:
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message, loop)

    def get_current_stream_id(self) -> str | None:
        queue_sink_pad = self._rtp_queue.get_static_pad("sink")
        return queue_sink_pad.get_stream_id()

    def on_message(self, bus: Gst.Bus, message: Gst.Message, loop: GLib.MainLoop) -> None:
        t = message.type
        if t == Gst.MessageType.EOS:
            logger.info("End-of-stream")
            self.terminate()
            loop.quit()
        elif t == Gst.MessageType.WARNING:
            err, debug = message.parse_warning()
            logger.warning(f"Warning: {err}: {debug}")
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Error: {err}: {debug}")
            self.terminate()
            loop.quit()

    def on_rtsp_src_pad_added(self, element: Gst.Element, pad: Gst.Pad) -> None:
        logger.debug(f"[Element = {element}] [Pad = {pad}] Trying to link rtp-queue to rtsp-source")
        rtp_rtp_queue_sink_pad = self._rtp_queue.get_static_pad("sink")
        assert rtp_rtp_queue_sink_pad
        if pad.link(rtp_rtp_queue_sink_pad) == Gst.PadLinkReturn.OK:
            logger.info(f"[Element = {element}] rtp-queue has been successfully linked to rtsp-source!")
        else:
            logger.error(f"[Element = {element}] rtp-queue could not be linked linked to rtsp-source!")

    def on_decoder_pad_added(self, decoder, pad, data):
        videoconvert_sink_pad = self._videoconvert.get_static_pad("sink")
        assert videoconvert_sink_pad

        # Check if the pad's caps are compatible with videoconvert's sink pad caps
        caps = pad.get_current_caps()
        if caps is None:
            caps = pad.query_caps()

        # Optionally, you can filter the pad based on its media type.
        structure = caps.get_structure(0)
        media_type = structure.get_name()
        logger.info(f"New pad added with type: {media_type}")

        # Attempt to link
        ret = pad.link(videoconvert_sink_pad)
        if ret == Gst.PadLinkReturn.OK:
            logger.info("Successfully linked decoder pad to videoconvert")
        else:
            logger.error(f"Failed to link decoder pad to videoconvert. Link return: {ret}")

    def start_pipeline(self, loop: GLib.MainLoop) -> None:
        logger.info(f"Starting pipeline for rtsp-url: {self.rtsp_url}.")
        self.add_bus_to_pipeline(loop)
        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise RuntimeError(f"Unable to set the pipeline for rtsp-url: {self.rtsp_url} to the playing state")
        self.state = RecordingState.RECORDING
        self._recording_started_time = time.time()

    def add_callback_probe(self, callback: Callable[[Gst.Pad, Gst.PadProbeInfo], Gst.PadProbeReturn]) -> None:
        app_tee_src_pad_0 = self._app_tee.get_static_pad("src_0")
        assert app_tee_src_pad_0
        return app_tee_src_pad_0.add_probe(Gst.PadProbeType.IDLE, callback)

    def _on_new_sample(self, sink, data) -> None:
        """
        Callback function that is invoked each time appsink has a new sample.
        It pulls the sample, maps the buffer, and converts it to a NumPy array.
        """
        sample = sink.emit("pull-sample")
        if sample is None:
            return Gst.FlowReturn.ERROR

        # Retrieve the buffer from the sample
        buffer = sample.get_buffer()
        # Retrieve the caps (capabilities) to get frame dimensions etc.
        caps = sample.get_caps()
        structure = caps.get_structure(0)
        # Read width, height from the caps; adjust these field names as needed.
        width = structure.get_value("width")
        height = structure.get_value("height")

        # Map the buffer so we can access its data
        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            logger.info("Could not map buffer data!")
            return Gst.FlowReturn.ERROR

        try:
            # Convert the mapped data to a NumPy array.
            # We assume the format is BGR (3 channels, 8-bit each) as set later in the pipeline.
            frame = np.frombuffer(map_info.data, dtype=np.uint8)
            # Reshape the array to [height, width, channels]
            frame = frame.reshape((height, width, 3))
            # Now you have a NumPy array representing the video frame.
            # You can process the frame here (e.g., run OpenCV operations).
            # logger.info(f"Received frame with shape: {frame.shape}")
            for callback in self._new_sample_callbacks:
                callback(frame)
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
        finally:
            # Unmap the buffer after processing
            buffer.unmap(map_info)

        return Gst.FlowReturn.OK

    def add_app_sink_new_sample_callback(self, callback: Callable[[np.array], None]) -> None:
        self._new_sample_callbacks.append(callback)

    def _sink_queue_probe_callback(self, pad, info):
        self.frames_consumed += 1
        return Gst.PadProbeReturn.OK

    def _start_recording_pad_callback(self, pad, info):
        assert self._file_sink_queue.set_state(Gst.State.NULL)
        assert self._mp4mux.set_state(Gst.State.NULL)
        assert self._file_sink.set_state(Gst.State.NULL)

        self._file_sink.set_property(
            "location",
            f"{self._recordings_directory}/{datetime.datetime.now().isoformat()}.mp4"
        )

        file_sink_queue_sink_pad = self._file_sink_queue.get_static_pad('sink')
        assert file_sink_queue_sink_pad
        assert pad.link(file_sink_queue_sink_pad) == Gst.PadLinkReturn.OK

        stream_id = self.get_current_stream_id()
        assert stream_id

        file_sink_queue_sink_pad = self._file_sink_queue.get_static_pad("sink")
        assert file_sink_queue_sink_pad
        file_sink_queue_sink_pad.send_event(Gst.Event.new_stream_start(stream_id))

        self._sink_tee.sync_state_with_parent()
        self._file_sink_queue.sync_state_with_parent()
        self._mp4mux.sync_state_with_parent()
        self._file_sink.sync_state_with_parent()

        self.state = RecordingState.RECORDING

        return Gst.PadProbeReturn.REMOVE

    def begin_starting_recording(self) -> None:
        logger.info(f"Starting recording!")

        self._last_recording_start_time = time.time()

        current_datetime = datetime.datetime.now()
        self._file_sink.set_property(
            "location",
            f"{self._recordings_directory}/recording-{self.recordings_counter}-date-{current_datetime.isoformat()}.mp4"
        )

        assert self._sink_tee_src_record_pad
        self._sink_tee_src_record_pad.add_probe(Gst.PadProbeType.IDLE, self._start_recording_pad_callback)

        if self.state != RecordingState.RECORDING:
            self.state = RecordingState.STARTING

    def _stop_recording_pad_callback(self, pad: Gst.Pad, info: Gst.PadProbeInfo) -> Gst.PadProbeReturn:
        if datetime.datetime.now() < self.stop_recording_time:
            # Recording should not be stopped yet
            return Gst.PadProbeReturn.PASS

        # Recording should be stopped -> file_sink_queue will be unlinked from tee element
        logger.info(f"Reached stopping in '_stop_recording_pad_callback'!")
        file_sink_queue_sink_pad = self._file_sink_queue.get_static_pad('sink')
        assert file_sink_queue_sink_pad
        assert pad
        pad.unlink(file_sink_queue_sink_pad)

        # End of stream message triggers the file write to finalise file writing including file headers/footers.
        file_sink_queue_sink_pad.send_event(Gst.Event.new_eos())

        # assert self._file_sink_queue.set_state(Gst.State.NULL)
        # assert self._mp4mux.set_state(Gst.State.NULL)
        # assert self._file_sink.set_state(Gst.State.NULL)

        self.state = RecordingState.STOPPED

        return Gst.PadProbeReturn.REMOVE

    def begin_stopping_recording(self) -> None:
        logger.info(f"Stopping recording on pipeline for = {self.camera_id}.")

        self._last_recording_stop_time = time.time()

        before_detection_buffer = self._recording_buffer
        after_detection_buffer = self._recording_buffer

        seconds_delta = after_detection_buffer / 1e9
        # because recording is "set-back-in-time" for before_detection_buffer
        # we must also add it to time-delta
        seconds_delta += before_detection_buffer / 1e9
        current_time = datetime.datetime.now()
        self.stop_recording_time = current_time + datetime.timedelta(seconds=seconds_delta)
        stopping_latency = self.stop_recording_time - current_time
        logger.info(f"Current time = {current_time.strftime('%H:%M:%S.%s')}")
        logger.info(f"Recording will be stopped in {self.stop_recording_time.strftime('%H:%M:%S.%s')}")
        logger.info(f"Stopping will take {stopping_latency.total_seconds()}")

        assert self._sink_tee
        assert self._sink_tee_src_record_pad
        self._sink_tee_src_record_pad.add_probe(
            Gst.PadProbeType.IDLE, self._stop_recording_pad_callback
        )
        if self.state != RecordingState.STOPPED:
            self.state = RecordingState.STOPPING

    def terminate(self) -> None:
        self.pipeline.set_state(Gst.State.NULL)

    def stop_after_5_seconds(self, loop) -> bool:
        _, position = self.pipeline.query_position(Gst.Format.TIME)
        print("Position: %s\r" % Gst.TIME_ARGS(position))

        if position > 5 * Gst.SECOND:
            print("Emitting EOS event to pipeline")
            self.pipeline.send_event(Gst.Event.new_eos())
            return False
        return True

    def switch_state(self) -> None:
        current_time = time.time()

        if self.state == RecordingState.RECORDING:
            logger.info("Trying to stop recording!")
            if current_time - self._last_recording_start_time > 5.0:
                logger.info("Beginning stopping recording!")
                self.begin_stopping_recording()
            else:
                logger.info("Recording cannot be stopped,"
                            " because the current recording "
                            "lasts less than 5 seconds!")
        elif self.state == RecordingState.STOPPED or self.state == RecordingState.NOT_STARTED:
            logger.info("Trying to start recording!")
            if current_time - self._last_recording_stop_time > 5.0:
                logger.info("Beginning starting recording!")
                self.begin_starting_recording()
            else:
                logger.info("Recording cannot be started, "
                            "because the previous recording "
                            "was created less than 5 seconds ago!")

    def new_recording_every_10_seconds(self, loop) -> bool:
        _, position = self.pipeline.query_position(Gst.Format.TIME)
        print("Position: %s\r" % Gst.TIME_ARGS(position))

        if position < 10 * Gst.SECOND:
            return True
        elif position % (10 * Gst.SECOND) < Gst.SECOND:
            self.switch_state()
        return True

    def sigint_handler(self, signum, frame) -> None:
        if self.state == RecordingState.RECORDING:
            self.begin_stopping_recording()
        else:
            self.begin_starting_recording()


if __name__ == "__main__":
    initialize_gstreamer()
    main_loop = GLib.MainLoop()

    os.environ["GST_DEBUG"] = "3"

    local_rtsp_url = "rtsp://mediamtx:8554/mystream"
    logger.info(f"Creating TrackingPipeline for stream {local_rtsp_url}")
    pipeline = TrackerPipeline(
        camera_id="some-camera-id",
        rtsp_url=local_rtsp_url,
        recordings_directory=Path("/data/videos")
    )
    logger.info(f"Successfully created TrackingPipeline for stream {local_rtsp_url}")

    GLib.timeout_add_seconds(1, pipeline.new_recording_every_10_seconds, main_loop)

    # signal.signal(signal.SIGINT, pipeline.sigint_handler)

    pipeline.start_pipeline(main_loop)

    try:
        main_loop.run()
    except Exception as e:
        logger.error(f"Exception during pipeline execution. Error = {e}")
        pass
