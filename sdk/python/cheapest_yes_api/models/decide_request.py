from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, OptionalNullable, SdkBaseModel
from .cart_item import CartItem, CartItemDict
from .session2 import Session2, Session2Dict


class DecideRequest(SdkBaseModel):
    """DecideRequest"""

    cart: list[CartItem]
    """cart"""

    session: Optional[Session2] = UNSET
    """session"""

    shopper_id: OptionalNullable[str] = UNSET
    """Opaque id for per-shopper caps; stored only as a hash"""


class DecideRequestDict(TypedDict):
    cart: list[CartItemDict]
    session: NotRequired[Session2Dict]
    shopper_id: NotRequired[str | None]
