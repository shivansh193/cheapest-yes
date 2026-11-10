from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Reason(SdkBaseModel):
    """Reason"""

    feature: str
    """feature"""

    value: float
    """value"""

    contribution: float
    """contribution"""

    text: str
    """text"""


class ReasonDict(TypedDict):
    feature: str
    value: float
    contribution: float
    text: str
