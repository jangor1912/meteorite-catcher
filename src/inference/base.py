from abc import ABC, abstractmethod

from src.types import NumpyImage, BBoxList


class BaseInferenceEngine(ABC):
    @abstractmethod
    def update(self, frame: NumpyImage) -> BBoxList:
        pass
