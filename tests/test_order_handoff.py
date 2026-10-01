import pytest

from marketplace_meter.order_handoff import BuyerUpdate, HandoffRequest, OrderLedger, SellerAsset


def test_buyer_usage_is_counted_once_and_handoff_closes_updates() -> None:
    ledger = OrderLedger()
    ledger.open_order(
        "order-1042",
        SellerAsset(asset_id="theme-canvas", seller_customer_id="seller-studio"),
    )
    update = BuyerUpdate(
        update_id="update-logo-1",
        buyer_customer_id="buyer-shop-42",
        usage_units=18,
    )

    first = ledger.record_buyer_update("order-1042", update)
    replay = ledger.record_buyer_update("order-1042", update)
    order = ledger.handoff("order-1042", HandoffRequest(handoff_id="handoff-1042"))

    assert first == replay
    assert ledger.customer_totals() == {"buyer-shop-42": 18}
    assert order.handed_off is True
    with pytest.raises(ValueError, match="no longer accept"):
        ledger.record_buyer_update(
            "order-1042",
            BuyerUpdate(
                update_id="update-after-handoff",
                buyer_customer_id="buyer-shop-42",
                usage_units=2,
            ),
        )

