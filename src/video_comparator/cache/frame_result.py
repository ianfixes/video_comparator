from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import numpy as np


class FrameRequestStatus(Enum):
    """
    Enum representing the status of a frame request, as produced by FrameCache.
    """

    SUCCESS = auto()  # Frame successfully retrieved and decoded.
    CANCELLED = auto()  # Request was cancelled (e.g., due to a new strategy request, race condition).
    DECODE_ERROR = auto()  # Frame decode failed.
    SEEK_ERROR = auto()  # Seeking to the frame failed.
    OUT_OF_RANGE = auto()  # Frame index requested is out of valid range.


@dataclass(frozen=True)
class FrameResult:
    """
    Represents the result of a frame request made to the FrameCache.

    Attributes:
        frame_number (int): The requested frame index.
        frame (Optional[np.ndarray]): The decoded frame data, if successful; None if request failed.
        status (FrameRequestStatus): Status indicating the result of the frame request.
        error (Optional[Exception]): Exception object providing error details for error statuses, None if not applicable.
    """

    frame_number: int
    frame: Optional[np.ndarray]
    status: FrameRequestStatus
    error: Optional[Exception] = None
