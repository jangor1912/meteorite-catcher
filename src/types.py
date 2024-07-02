from typing import Annotated, Literal

import numpy as np
import numpy.typing as npt

# 8-bit Image with 3 color channels
NumpyImage = Annotated[npt.NDArray[np.int8], Literal["N", "N", 3]]

# List with N elements
# Every BBox is a 5-dim vector [x0, y0, x1, y1, score]
BBoxList = Annotated[npt.NDArray[np.float32], Literal["N", 5]]
