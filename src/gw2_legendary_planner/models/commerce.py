from __future__ import annotations

from pydantic import Field

from gw2_legendary_planner.models.account import ApiModel


class CommerceListingSummary(ApiModel):
    """Aggregated trading-post listing side for one item."""

    quantity: int = 0
    unit_price: int = 0


class CommercePrice(ApiModel):
    """Current GW2 trading-post price summary for one item."""

    id: int
    whitelisted: bool = True
    buys: CommerceListingSummary = Field(default_factory=CommerceListingSummary)
    sells: CommerceListingSummary = Field(default_factory=CommerceListingSummary)
