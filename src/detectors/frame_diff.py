from dataclasses import field, dataclass
from typing import Optional

import cv2
import numpy as np

from src.detectors.base import BaseDetector
from src.detectors.functions import get_detections
from src.types import NumpyImage, BBoxList


@dataclass
class FrameDiffDetector(BaseDetector):
    bbox_threshold: float = 100
    nms_threshold: float = 1e-3
    _previous_frame: Optional[NumpyImage] = field(init=False, default=None)

    def update(self, frame: NumpyImage) -> BBoxList:
        if self._previous_frame is None:
            bboxes = np.zeros((0, 5), dtype=np.float32)
        else:
            bboxes = get_detections(
                frame1=cv2.cvtColor(self._previous_frame, cv2.COLOR_BGR2GRAY),
                frame2=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                bbox_thresh=self.bbox_threshold,
                nms_thresh=self.nms_threshold
            )
        self._previous_frame = frame
        return bboxes.astype(np.float32)
