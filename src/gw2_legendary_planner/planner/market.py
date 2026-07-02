from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field

from gw2_legendary_planner.models.commerce import CommercePrice
from gw2_legendary_planner.planner.recipes import RequirementKind
from gw2_legendary_planner.planner.shopping_list import (
    ShoppingListEntry,
    ShoppingListGoal,
    ShoppingListReport,
)

ShoppingListPriceStatus = Literal[
    "priced",
    "complete",
    "not_item",
    "no_market_price",
    "not_whitelisted",
    "no_sell_listing",
]


class ShoppingListPriceEntry(BaseModel):
    """Trading-post price estimate for one shopping-list entry."""

    kind: RequirementKind
    id: int | str
    name: str | None = None
    missing_quantity: int
    price_status: ShoppingListPriceStatus
    buy_order_unit_price: int | None = None
    sell_listing_unit_price: int | None = None
    estimated_buy_cost: int | None = None
    estimated_sell_value: int | None = None
    note: str | None = None

    @property
    def is_priced(self) -> bool:
        return self.price_status == "priced"


class ShoppingListPriceReport(BaseModel):
    """Optional market-price overlay for a recipe shopping list."""

    goals: list[ShoppingListGoal] = Field(default_factory=list)
    entries: list[ShoppingListPriceEntry] = Field(default_factory=list)
    priced_entry_count: int = 0
    unpriced_entry_count: int = 0
    total_estimated_buy_cost: int = 0
    total_estimated_sell_value: int = 0
    price_source: str = "gw2_commerce_prices"


def price_shopping_list(
    report: ShoppingListReport,
    prices: Mapping[int, CommercePrice],
) -> ShoppingListPriceReport:
    """Estimate trading-post value for item requirements in a shopping list."""

    entries = [_price_entry(entry, prices) for entry in report.entries]
    priced_entries = [entry for entry in entries if entry.is_priced]
    unpriced_entries = [
        entry
        for entry in entries
        if entry.missing_quantity > 0 and not entry.is_priced
    ]
    return ShoppingListPriceReport(
        goals=report.goals,
        entries=entries,
        priced_entry_count=len(priced_entries),
        unpriced_entry_count=len(unpriced_entries),
        total_estimated_buy_cost=sum(
            entry.estimated_buy_cost or 0 for entry in priced_entries
        ),
        total_estimated_sell_value=sum(
            entry.estimated_sell_value or 0 for entry in priced_entries
        ),
    )


def shopping_list_price_item_ids(report: ShoppingListReport) -> list[int]:
    """Return unique item ids that can be looked up through commerce prices."""

    item_ids = [
        entry.id
        for entry in report.entries
        if entry.kind == "item"
        and isinstance(entry.id, int)
        and entry.missing_quantity > 0
    ]
    return list(dict.fromkeys(item_ids))


def _price_entry(
    entry: ShoppingListEntry,
    prices: Mapping[int, CommercePrice],
) -> ShoppingListPriceEntry:
    if entry.missing_quantity <= 0:
        return _unpriced_entry(entry, "complete", "No missing quantity.")
    if entry.kind != "item" or not isinstance(entry.id, int):
        return _unpriced_entry(entry, "not_item", "Only item requirements have market prices.")

    price = prices.get(entry.id)
    if price is None:
        return _unpriced_entry(
            entry,
            "no_market_price",
            "No trading-post price was available for this item.",
        )
    if not price.whitelisted:
        return _unpriced_entry(
            entry,
            "not_whitelisted",
            "The item is not currently whitelisted for trading-post pricing.",
            price=price,
        )
    if price.sells.unit_price <= 0:
        return _unpriced_entry(
            entry,
            "no_sell_listing",
            "No sell listing was available for an instant buy estimate.",
            price=price,
        )

    return ShoppingListPriceEntry(
        kind=entry.kind,
        id=entry.id,
        name=entry.name,
        missing_quantity=entry.missing_quantity,
        price_status="priced",
        buy_order_unit_price=price.buys.unit_price,
        sell_listing_unit_price=price.sells.unit_price,
        estimated_buy_cost=entry.missing_quantity * price.sells.unit_price,
        estimated_sell_value=entry.missing_quantity * price.buys.unit_price,
    )


def _unpriced_entry(
    entry: ShoppingListEntry,
    status: ShoppingListPriceStatus,
    note: str,
    *,
    price: CommercePrice | None = None,
) -> ShoppingListPriceEntry:
    return ShoppingListPriceEntry(
        kind=entry.kind,
        id=entry.id,
        name=entry.name,
        missing_quantity=entry.missing_quantity,
        price_status=status,
        buy_order_unit_price=price.buys.unit_price if price else None,
        sell_listing_unit_price=price.sells.unit_price if price else None,
        estimated_buy_cost=None,
        estimated_sell_value=None,
        note=note,
    )
