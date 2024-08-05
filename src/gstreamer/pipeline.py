import logging
import sys

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstBase', '1.0')

gi.require_version('Gtk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')

from gi.repository import GLib, Gst


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()


class TrackerPipeline:
    def __init__(self, camera_id: str):
        self.camera_id = camera_id

        self.pipeline = Gst.Pipeline.new(f"till-{self.camera_id}")

        self._rtsp_source = None
        self._rtp_queue = None
        self._depay = None
        self._h264parser = None


if __name__ == "__main__":
    logger.info("Hello World")
