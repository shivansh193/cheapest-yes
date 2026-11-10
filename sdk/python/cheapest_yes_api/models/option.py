from __future__ import annotations

from typing_extensions import TypedDict

from ..core import SdkBaseModel


class Option(SdkBaseModel):
    """Option"""

    incentive: str
    """incentive"""

    allowed: bool
    """allowed"""

    blocked_by: str | None
    """blocked by"""

    p_buy: float
    """p buy"""

    p_paylater: float
    """p paylater"""

    profit_if_buy: float
    """profit if buy"""

    expected_profit: float
    """expected profit"""

    gain_vs_none: float
    """gain vs none"""

    expected_spend: float
    """expected spend"""


class OptionDict(TypedDict):
    incentive: str
    allowed: bool
    blocked_by: str | None
    p_buy: float
    p_paylater: float
    profit_if_buy: float
    expected_profit: float
    gain_vs_none: float
    expected_spend: float
