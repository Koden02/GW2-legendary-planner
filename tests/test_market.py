from gw2_legendary_planner.models.commerce import CommercePrice
from gw2_legendary_planner.planner.market import (
    price_shopping_list,
    shopping_list_price_item_ids,
)
from gw2_legendary_planner.planner.shopping_list import (
    ShoppingListEntry,
    ShoppingListReport,
)


def test_price_shopping_list_estimates_buy_costs_for_item_requirements() -> None:
    report = ShoppingListReport(
        entries=[
            ShoppingListEntry(
                kind="item",
                id=1,
                name="Tradable Item",
                required_quantity=10,
                available_quantity=4,
                missing_quantity=6,
                readiness_percent=40,
            ),
            ShoppingListEntry(
                kind="currency",
                id=23,
                name="Spirit Shards",
                required_quantity=20,
                available_quantity=5,
                missing_quantity=15,
                readiness_percent=25,
            ),
            ShoppingListEntry(
                kind="item",
                id=2,
                name="Complete Item",
                required_quantity=1,
                available_quantity=1,
                missing_quantity=0,
                readiness_percent=100,
            ),
        ]
    )

    price_report = price_shopping_list(
        report,
        {
            1: CommercePrice(
                id=1,
                buys={"quantity": 20, "unit_price": 80},
                sells={"quantity": 12, "unit_price": 125},
            )
        },
    )
    by_name = {entry.name: entry for entry in price_report.entries}

    assert shopping_list_price_item_ids(report) == [1]
    assert price_report.priced_entry_count == 1
    assert price_report.unpriced_entry_count == 1
    assert price_report.total_estimated_buy_cost == 750
    assert price_report.total_estimated_sell_value == 480
    assert by_name["Tradable Item"].price_status == "priced"
    assert by_name["Tradable Item"].estimated_buy_cost == 750
    assert by_name["Spirit Shards"].price_status == "not_item"
    assert by_name["Complete Item"].price_status == "complete"


def test_price_shopping_list_marks_unmarketable_item_statuses() -> None:
    report = ShoppingListReport(
        entries=[
            ShoppingListEntry(
                kind="item",
                id=1,
                name="Missing Price",
                required_quantity=1,
                available_quantity=0,
                missing_quantity=1,
                readiness_percent=0,
            ),
            ShoppingListEntry(
                kind="item",
                id=2,
                name="Not Whitelisted",
                required_quantity=1,
                available_quantity=0,
                missing_quantity=1,
                readiness_percent=0,
            ),
            ShoppingListEntry(
                kind="item",
                id=3,
                name="No Listing",
                required_quantity=1,
                available_quantity=0,
                missing_quantity=1,
                readiness_percent=0,
            ),
        ]
    )

    price_report = price_shopping_list(
        report,
        {
            2: CommercePrice(id=2, whitelisted=False),
            3: CommercePrice(id=3, sells={"quantity": 0, "unit_price": 0}),
        },
    )
    statuses = {entry.name: entry.price_status for entry in price_report.entries}

    assert statuses == {
        "Missing Price": "no_market_price",
        "Not Whitelisted": "not_whitelisted",
        "No Listing": "no_sell_listing",
    }
