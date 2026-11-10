from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Amounts1(SdkBaseModel):
    """amounts"""

    item_total: float
    """item total"""

    shipping: float
    """shipping"""

    discount: float
    """discount"""

    total: float
    """total"""


class Amounts1Dict(TypedDict):
    item_total: float
    shipping: float
    discount: float
    total: float
