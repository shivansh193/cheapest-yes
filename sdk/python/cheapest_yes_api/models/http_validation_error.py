from __future__ import annotations

from typing_extensions import NotRequired, TypedDict

from ..core import UNSET, Optional, SdkBaseModel
from .validation_error import ValidationError, ValidationErrorDict


class HttpValidationError(SdkBaseModel):
    """Request failed validation."""

    detail: Optional[list[ValidationError]] = UNSET
    """detail"""


class HttpValidationErrorDict(TypedDict):
    detail: NotRequired[list[ValidationErrorDict]]
