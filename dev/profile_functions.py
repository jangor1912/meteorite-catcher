from pathlib import Path
from pstats import Stats, SortKey
from cProfile import Profile

import cv2
import numpy as np
from PIL import Image

from src.file_operations.images import draw_tracks_numpy
from src.detectors.functions import get_detections

PROJECT_DIRECTORY = Path(__file__).parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
IMAGES_DIRECTORY = DATA_DIRECTORY / "images"


def profile_detections(frame1_bgr, frame2_bgr) -> None:
    with Profile() as profile:
        get_detections(
            cv2.cvtColor(frame1_bgr, cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(frame2_bgr, cv2.COLOR_BGR2GRAY),
            bbox_thresh=128,
            nms_thresh=1e-3,
            mask_kernel=np.array((16, 16), dtype=np.uint8))
        (
            Stats(profile)
            .strip_dirs()
            .sort_stats(SortKey.CALLS)
            .print_stats()
        )


if __name__ == '__main__':
    video_name = "dim-meteorite-full-res"

    images_directory = IMAGES_DIRECTORY / video_name

    first_image_path = images_directory / "011.png"
    second_image_path = images_directory / "012.png"

    first_image = cv2.imread(str(first_image_path))
    second_image = cv2.imread(str(second_image_path))

    # detections = get_detections(
    #     cv2.cvtColor(first_image, cv2.COLOR_BGR2GRAY),
    #     cv2.cvtColor(second_image, cv2.COLOR_BGR2GRAY),
    #     bbox_thresh=128,
    #     nms_thresh=1e-3,
    #     mask_kernel=np.array((16, 16), dtype=np.uint8))
    #
    # draw_tracks_numpy(first_image, detections)
    #
    # im = Image.fromarray(first_image)
    # im.save("your_file.jpeg")

    profile_detections(first_image, second_image)
