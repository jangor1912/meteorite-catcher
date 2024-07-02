import os
import re
from glob import glob
from pathlib import Path

from PIL import Image

import cv2
from matplotlib import pyplot as plt

from src.types import NumpyImage, BBoxList


def get_image_paths(images_dir: Path, image_extension: str) -> list[str]:
    image_paths = sorted(glob(f"{images_dir}/*.{image_extension}"),
                         key=lambda x: float(re.findall(r"(\d+)", x)[0]))
    return image_paths


def draw_tracks_numpy(frame: NumpyImage, tracks: BBoxList):
    for det in tracks:
        cv2.rectangle(
            frame,
            (int(det[0]),int(det[1])),
            (int(det[2]),int(det[3])),
            (0,255,0), 3
        )


def save_numpy_image(image: NumpyImage, image_output_path: Path) -> None:
    im = Image.fromarray(image)
    im.save(str(image_output_path.absolute()))


def save_as_plot(image: NumpyImage, image_output_path: Path) -> None:
    fig = plt.figure(figsize=(15, 7))
    plt.imshow(image)
    plt.axis('off')
    fig.savefig(str(image_output_path.absolute()))
    plt.close()


def create_gif_from_images(save_path : str, image_path : str, ext : str) -> None:
    """ Creates a GIF from a folder of images
        Inputs:
            save_path - path to save GIF
            image_path - path where images are located
            ext - extension of the images
        Outputs:
            None
    """
    ext = ext.replace('.', '')
    image_paths = sorted(glob(os.path.join(image_path, f'*.{ext}')))
    image_paths.sort(key=lambda f: int(''.join(filter(str.isdigit, f))))
    pil_images = [Image.open(im_path) for im_path in image_paths]

    pil_images[0].save(save_path, format='GIF', append_images=pil_images,
                       save_all=True, duration=50, loop=0)
