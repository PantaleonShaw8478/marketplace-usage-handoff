from fastapi.testclient import TestClient

from marketplace_meter.storefront_service import service


def main() -> None:
    client = TestClient(service)
    order_id = "order-demo-1042"
    client.post(
        f"/orders/{order_id}",
        json={"asset_id": "theme-canvas", "seller_customer_id": "seller-studio"},
    ).raise_for_status()
    metered = client.post(
        f"/orders/{order_id}/buyer-updates",
        json={
            "update_id": "update-logo-1",
            "buyer_customer_id": "buyer-shop-42",
            "usage_units": 18,
        },
    )
    metered.raise_for_status()
    handoff = client.post(
        f"/orders/{order_id}/handoff",
        json={"handoff_id": "handoff-1042"},
    )
    handoff.raise_for_status()
    print({"metered": metered.json()["metered"], "order": handoff.json()})


if __name__ == "__main__":
    main()

