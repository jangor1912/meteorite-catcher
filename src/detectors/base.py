from abc import ABC, abstractmethod

from src.types import BBoxList, NumpyImage


class BaseDetector(ABC):
    @abstractmethod
    def update(self, frame: NumpyImage) -> BBoxList:
        pass
