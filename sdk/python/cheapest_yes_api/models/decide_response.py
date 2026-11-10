from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel
from .amounts1 import Amounts1, Amounts1Dict
from .option import Option, OptionDict
from .reason import Reason, ReasonDict


class DecideResponse(SdkBaseModel):
    """DecideResponse"""

    decision_id: str
    """decision id"""

    incentive: str
    """one of: none, paylater, free_shipping, addon, discount_5, discount_10"""

    label: str
    """label"""

    amounts: Amounts1
    """amounts"""

    expected_gain: float
    """expected profit vs no incentive, USD"""

    explanation: str
    """explanation"""

    reasons: list[Reason]
    """reasons"""

    options: list[Option]
    """options"""

    guardrails: list[str]
    """guardrails"""


class DecideResponseDict(TypedDict):
    decision_id: str
    incentive: str
    label: str
    amounts: Amounts1Dict
    expected_gain: float
    explanation: str
    reasons: list[ReasonDict]
    options: list[OptionDict]
    guardrails: list[str]
