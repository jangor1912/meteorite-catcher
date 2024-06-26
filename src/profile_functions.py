from pstats import Stats, SortKey
from cProfile import Profile

import cv2
import numpy as np

from src.frame_difference_detection.detector import get_detections


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