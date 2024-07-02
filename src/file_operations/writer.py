from dataclasses import dataclass
from pathlib import Path

from src.file_operations.images import save_numpy_image, save_as_plot
from src.types import NumpyImage


@dataclass
class ImageWriter:
    output_directory: Path
    image_extension: str = "png"
    quick: bool = True
    _image_number: int = 0

    def save(self, image: NumpyImage) -> None:
        if self.quick:
            save_as_plot(
                image=image,
                image_output_path=self.output_directory / f"{self._image_number}.{self.image_extension}",
            )
        else:
            save_numpy_image(
                image=image,
                image_output_path=self.output_directory / f"{self._image_number}.{self.image_extension}",
            )
        self._image_number += 1
