import argparse
import logging
import sys
from pathlib import Path

from ioutrack import Sort

from src.detectors.frame_diff import FrameDiffDetector
from src.gstreamer.detector_controller import DetectorController
from src.gstreamer.pipeline import initialize_gstreamer, TrackerPipeline

import gi

from src.inference.inference import FrameDiffInference

gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')

from gi.repository import GLib, Gst

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger()

PROJECT_DIRECTORY = Path(__file__).parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
IMAGES_DIRECTORY = DATA_DIRECTORY / "images"
VIDEOS_DIRECTORY = DATA_DIRECTORY / "videos"
OUTPUT_DIRECTORY = DATA_DIRECTORY / "output"


def run_pipeline(
        rtsp_url: str,
        data_dir: Path,
        bbox_threshold: int = 128,
        nms_threshold: float = 1e-3,
        tracker_min_hits: int = 3,
        tracker_max_age: int = 5,
        recording_buffer: int = 3000000000
) -> None:
    initialize_gstreamer()
    main_loop = GLib.MainLoop()

    logger.info(f"Creating TrackingPipeline for stream {rtsp_url}")
    pipeline = TrackerPipeline(
        camera_id="some-camera-id",
        rtsp_url=rtsp_url,
        recordings_directory=data_dir,
        recording_buffer=recording_buffer
    )
    logger.info(f"Successfully created TrackingPipeline for stream {rtsp_url}")

    inference_engine = FrameDiffInference(
        detector=FrameDiffDetector(
            bbox_threshold=bbox_threshold,
            nms_threshold=nms_threshold
        ),
        tracker=Sort(
            min_hits=tracker_min_hits,
            max_age=tracker_max_age
        )
    )

    controller = DetectorController(
        inference_engine=inference_engine,
        pipeline=pipeline,
        image_output_directory=data_dir,
    )

    pipeline.add_callback_probe(controller.switch_on_record_manager_callback)

    pipeline.add_app_sink_new_sample_callback(controller.update_with_frame)

    pipeline.start_pipeline(main_loop)

    try:
        main_loop.run()
    except Exception as e:
        logger.error(f"Exception during pipeline execution. Error = {e}")
        raise e


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--rtsp-url", help="RTSP URL of camera stream", type=str)
    parser.add_argument("--data-dir", help="Directory to save data to", type=str)
    parser.add_argument("--bbox-th", help="Bounding Box area threshold in pixels", type=int)
    parser.add_argument("--nms-th", help="Non-Maximum Suppression threshold (IOU threshold)", type=float)
    parser.add_argument(
        "--min-hits",
        help="Minimum number of successive detections to start recording",
        type=int
    )
    parser.add_argument(
        "--max-age",
        help="Maximum frames without matching detections before stopping recording",
        type=int
    )

    args = parser.parse_args()

    run_pipeline(
        rtsp_url=args.rtsp_url,
        data_dir=Path(args.data_dir),
        bbox_threshold=args.bbox_th,
        nms_threshold=args.nms_th,
        tracker_min_hits=args.min_hits,
        tracker_max_age=args.max_age
    )


if __name__ == "__main__":
    main()
