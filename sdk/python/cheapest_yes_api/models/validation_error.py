from __future__ import annotations

from typing import Any

from pydantic import Field
from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .unions.loc import Loc, LocDict


class ValidationError(SdkBaseModel):
    """One validation problem."""

    loc: list[Loc]
    """loc"""

    msg: str
    """msg"""

    type_: str = Field(alias="type")
    """type"""

    input: Optional[Any] = UNSET
    """input"""

    ctx: Optional[Any] = UNSET
    """ctx"""


class ValidationErrorDict(TypedDict):
    loc: list[LocDict]
    msg: str
    type_: str
    input: NotRequired[Any]
    ctx: NotRequired[Any]
