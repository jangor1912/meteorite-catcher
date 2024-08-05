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
