from pathlib import Path

import cv2
import numpy as np
from ioutrack import Sort

from src.file_operations.images import get_image_paths, create_gif_from_images, draw_tracks_numpy, save_numpy_image
from src.frame_difference_detection.detector import get_detections

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


def main() -> None:
    video_name = "meteorite-vertical"

    images_directory = IMAGES_DIRECTORY / video_name

    image_paths = get_image_paths(images_directory, "png")

    output_directory = OUTPUT_DIRECTORY / video_name
    output_directory.mkdir(exist_ok=True, parents=True)

    draw_tracks_on_images(
        image_paths=image_paths,
        output_directory=output_directory
    )

    create_gif_from_images(
        str(output_directory / f"{video_name}.gif"),
        str(output_directory),
        ".png"
    )


if __name__ == "__main__":
    main()

