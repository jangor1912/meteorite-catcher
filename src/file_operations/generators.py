from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import cv2

from src.file_operations.images import get_image_paths
from src.types import NumpyImage


@dataclass
class ImageGenerator:
    images_directory: Path
    image_extension: str = "png"
    image_paths: list[Path] = field(init=False, default_factory=list)

    def __post_init__(self):
        image_paths = get_image_paths(
            images_dir=self.images_directory,
            image_extension=self.image_extension
        )
        self.image_paths = [Path(image_path) for image_path in image_paths]

    def __iter__(self) -> Iterator[NumpyImage]:
        for image_path in self.image_paths:
            image = cv2.imread(str(image_path.absolute()))
            yield image

    def __len__(self) -> int:
        return len(self.image_paths)
