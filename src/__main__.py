from pathlib import Path

import cv2
from ioutrack import Sort
from matplotlib import pyplot as plt

from src.file_operations.images import get_image_paths, draw_tracks, create_gif_from_images
from src.frame_difference_detection.detector import get_detections, detections_to_numpy_array
# from src.profile_functions import profile_detections

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
    detections_1_numpy = detections_to_numpy_array(detections_1)
    tracker.update(detections_1_numpy, return_all=False)

    tracks = list()

    while idx < len(image_paths):
        # read frames
        frame3_bgr = cv2.imread(image_paths[idx])

        # get detections
        detections_2 = get_detections(cv2.cvtColor(frame2_bgr, cv2.COLOR_BGR2GRAY),
                                      cv2.cvtColor(frame3_bgr, cv2.COLOR_BGR2GRAY),
                                      bbox_thresh=128,
                                      nms_thresh=1e-3)

        detections_2_numpy = detections_to_numpy_array(detections_2)
        tracks = tracker.update(detections_2_numpy, return_all=False)

        # draw only after initial period
        if idx > min_hits:
            # draw bounding boxes on frame
            draw_tracks(frame2_bgr, tracks)

        # save image for GIF
        fig = plt.figure(figsize=(15, 7))
        plt.imshow(frame2_bgr)
        plt.axis('off')
        fig.savefig(f"{output_directory}/frame_{idx - 1}.png")
        plt.close()

        # increment index
        frame1_bgr = frame2_bgr
        frame2_bgr = frame3_bgr
        detections_1 = detections_2
        idx += 1


def main() -> None:
    video_name = "meteorite-exploding"

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

