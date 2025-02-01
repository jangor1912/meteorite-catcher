import sys
import gi
import numpy as np

gi.require_version("Gst", "1.0")
gi.require_version("GstApp", "1.0")
from gi.repository import Gst, GLib, GstApp

# Initialize GStreamer
Gst.init(None)


def on_new_sample(sink, data):
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
        print("Could not map buffer data!")
        return Gst.FlowReturn.ERROR

    try:
        # Convert the mapped data to a NumPy array.
        # We assume the format is BGR (3 channels, 8-bit each) as set later in the pipeline.
        frame = np.frombuffer(map_info.data, dtype=np.uint8)
        # Reshape the array to [height, width, channels]
        frame = frame.reshape((height, width, 3))
        # Now you have a NumPy array representing the video frame.
        # You can process the frame here (e.g., run OpenCV operations).
        print("Received frame with shape:", frame.shape)
    except Exception as e:
        print("Error processing frame:", e)
    finally:
        # Unmap the buffer after processing
        buffer.unmap(map_info)

    return Gst.FlowReturn.OK


def main():
    # Replace the RTSP URL with your actual stream URL.
    rtsp_url = "rtsp://mediamtx:8554/mystream"

    # Build the GStreamer pipeline.
    #
    # The pipeline:
    #   - rtspsrc: retrieves the RTSP stream.
    #   - decodebin: auto-detects and decodes the stream.
    #   - videoconvert: converts the video format.
    #   - capsfilter: forces the output video format (here: raw BGR video).
    #   - appsink: allows pulling frames into the application.
    #
    # The appsink is named "appsink0" for later reference.
    pipeline_description = (
        f"rtspsrc location={rtsp_url} latency=200 ! "
        "rtph264depay ! h264parse ! decodebin3 ! "
        "videoconvert ! video/x-raw, format=BGR ! "
        "appsink name=appsink0"
    )

    # Create the pipeline from the description string
    pipeline = Gst.parse_launch(pipeline_description)

    # Retrieve the appsink element by name
    appsink = pipeline.get_by_name("appsink0")
    if not appsink:
        print("Could not retrieve appsink element from the pipeline.")
        sys.exit(1)

    # Configure appsink: make it emit signals (for new-sample) and optionally set other properties.
    appsink.set_property("emit-signals", True)
    appsink.set_property("sync", False)  # Set sync=False to process frames as fast as they arrive.
    appsink.connect("new-sample", on_new_sample, None)

    # Start playing the pipeline
    pipeline.set_state(Gst.State.PLAYING)
    print("Pipeline started. Listening for frames...")

    # Create and run a GLib Main Loop to process GStreamer messages and callbacks.
    loop = GLib.MainLoop()

    try:
        loop.run()
    except KeyboardInterrupt:
        print("Interrupted by user. Exiting...")
    finally:
        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
