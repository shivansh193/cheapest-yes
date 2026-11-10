from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Amounts(SdkBaseModel):
    """Amounts"""

    item_total: float
    """item total"""

    shipping: float
    """shipping"""

    discount: float
    """discount"""

    total: float
    """total"""


class AmountsDict(TypedDict):
    item_total: float
    shipping: float
    discount: float
    total: float
