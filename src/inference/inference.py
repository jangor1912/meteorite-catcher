from dataclasses import dataclass, field

import numpy as np
from ioutrack import BaseTracker
from src.detectors.base import BaseDetector
from src.inference.base import BaseInferenceEngine
from src.types import NumpyImage, BBoxList


@dataclass
class FrameDiffInference(BaseInferenceEngine):
    detector: BaseDetector
    tracker: BaseTracker
    min_hits: int = 5
    _frames_passed: int = field(init=False, default=0)

    def update(self, frame: NumpyImage) -> BBoxList:
        bboxes = self.detector.update(frame)
        bboxes = self.tracker.update(bboxes, return_all=False)
        self._frames_passed += 1
        if self._frames_passed < self.min_hits:
            return np.zeros(shape=np.zeros((0, 5), dtype=np.float32))
        return bboxes
