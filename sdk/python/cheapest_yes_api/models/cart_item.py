from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, OptionalNullable, SdkBaseModel


class CartItem(SdkBaseModel):
    """CartItem"""

    id: str
    """Product id (catalog id for the demo store)"""

    title: str = ""
    """Product name"""

    price: float
    """List price in USD"""

    qty: int = 1
    """qty"""

    brand: OptionalNullable[str] = UNSET
    """brand"""

    image: OptionalNullable[str] = UNSET
    """image"""


class CartItemDict(TypedDict):
    id: str
    title: NotRequired[str]
    price: float
    qty: NotRequired[int]
    brand: NotRequired[str | None]
    image: NotRequired[str | None]
