import logging
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from ioutrack import Sort

from src.detectors.frame_diff import FrameDiffDetector
from src.file_operations.generators import ImageGenerator
from src.file_operations.images import draw_tracks_numpy, save_numpy_image
from src.detectors.functions import get_detections
from src.file_operations.writer import ImageWriter

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

PROJECT_DIRECTORY = Path(__file__).parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
IMAGES_DIRECTORY = DATA_DIRECTORY / "images"
OUTPUT_DIRECTORY = DATA_DIRECTORY / "output"


def draw_tracks_on_images(image_paths: list[str], output_directory: Path) -> None:
    min_hits = 5
    max_age = 5

    tracker = Sort(max_age=max_age, min_hits=min_hits)

    idx = 2
    frame1_bgr = cv2.imread(image_paths[idx - 2])
    frame2_bgr = cv2.imread(image_paths[idx - 1])

    detections_1 = get_detections(cv2.cvtColor(frame1_bgr, cv2.COLOR_BGR2GRAY),
                                  cv2.cvtColor(frame2_bgr, cv2.COLOR_BGR2GRAY),
                                  bbox_thresh=128,
                                  nms_thresh=1e-3)

    tracker.update(detections_1.astype(np.float32), return_all=False)

    while idx < len(image_paths):
        # read frames
        frame3_bgr = cv2.imread(image_paths[idx])

        # get detections
        detections_2 = get_detections(cv2.cvtColor(frame2_bgr, cv2.COLOR_BGR2GRAY),
                                      cv2.cvtColor(frame3_bgr, cv2.COLOR_BGR2GRAY),
                                      bbox_thresh=128,
                                      nms_thresh=1e-3)
        tracks = tracker.update(detections_2.astype(np.float32), return_all=False)

        # draw only after initial period
        if idx > min_hits:
            # draw bounding boxes on frame
            draw_tracks_numpy(frame2_bgr, tracks)

        # save image for GIF
        save_numpy_image(
            image=frame2_bgr,
            image_output_path=output_directory / f"frame_{idx - 1}.png"
        )

        # increment index
        frame1_bgr = frame2_bgr
        frame2_bgr = frame3_bgr
        detections_1 = detections_2
        idx += 1


def draw_tracks(image_directory: Path, output_directory: Path) -> None:
    image_generator = ImageGenerator(images_directory=image_directory)
    detector = FrameDiffDetector(bbox_threshold=128, nms_threshold=1e-3)
    tracker = Sort(min_hits=5, max_age=5)
    image_writer = ImageWriter(output_directory=output_directory)

    images_number = len(image_generator)

    for i, image in enumerate(image_generator):
        logging.info(f"Processing image {i} / {images_number}")
        start_time = time.time()

        bboxes = detector.update(image)
        bboxes = tracker.update(bboxes, return_all=False)

        inference_time = time.time()

        logging.info(f"\tInference latency: {inference_time - start_time}")

        draw_tracks_numpy(
            frame=image,
            tracks=bboxes
        )

        image_writer.save(image)

        writing_time = time.time()
        logging.info(f"\tWriting image latency: {writing_time - inference_time}")

        logging.info(f"\tFinished. Took {writing_time - start_time}")


def main() -> None:
    video_name = "meteorite-exploding"

    images_directory = IMAGES_DIRECTORY / video_name

    # image_paths = get_image_paths(images_directory, "png")

    output_directory = OUTPUT_DIRECTORY / video_name
    output_directory.mkdir(exist_ok=True, parents=True)

    # draw_tracks_on_images(
    #     image_paths=image_paths,
    #     output_directory=output_directory
    # )
    #
    # create_gif_from_images(
    #     str(output_directory / f"{video_name}.gif"),
    #     str(output_directory),
    #     ".png"
    # )

    draw_tracks(
        image_directory=images_directory,
        output_directory=output_directory
    )


if __name__ == "__main__":
    main()

