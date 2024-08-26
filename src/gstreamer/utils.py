from enum import Enum

import numpy as np
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstApp', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstBase', '1.0')

gi.require_version('Gtk', '3.0')
gi.require_version('GLib', '2.0')
gi.require_version('GObject', '2.0')

from gi.repository import GLib, Gst


class RecordingState(Enum):
    NOT_STARTED = "NOT_STARTED"
    STARTING = "STARTING"
    RECORDING = "RECORDING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"

    def next_state(self) -> "RecordingState":
        match self:
            case RecordingState.NOT_STARTED:
                return RecordingState.STARTING
            case RecordingState.STARTING:
                return RecordingState.RECORDING
            case RecordingState.RECORDING:
                return RecordingState.STOPPING
            case RecordingState.STOPPING:
                return RecordingState.STOPPED
            case RecordingState.STOPPED:
                return RecordingState.NOT_STARTED


def gst_to_numpy(buf: Gst.Buffer, caps: Gst.Caps) -> np.ndarray:
    channels = buf.get_size() // (caps.get_structure(0).get_value('height') * caps.get_structure(0).get_value('width'))
    arr: np.ndarray = np.ndarray(
        (
            caps.get_structure(0).get_value('height'),
            caps.get_structure(0).get_value('width'),
            channels
        ),
        buffer=buf.extract_dup(0, buf.get_size()),
        dtype=np.uint8,
    )
    return arr
