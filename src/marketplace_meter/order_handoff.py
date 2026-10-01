from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from pydantic import BaseModel, Field


class SellerAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    seller_customer_id: str = Field(min_length=1)


class BuyerUpdate(BaseModel):
    update_id: str = Field(min_length=1)
    buyer_customer_id: str = Field(min_length=1)
    usage_units: int = Field(gt=0)


class HandoffRequest(BaseModel):
    handoff_id: str = Field(min_length=1)


class MeteredUsage(BaseModel):
    order_id: str
    customer_id: str
    source_id: str
    kind: str
    usage_units: int


class OrderView(BaseModel):
    order_id: str
    asset_id: str
    seller_customer_id: str
    buyer_customer_id: str | None
    handed_off: bool
    metered_units: int


@dataclass
class _Order:
    asset: SellerAsset
    buyer_customer_id: str | None = None
    handed_off: bool = False
    metered_units: int = 0


class OrderLedger:
    """In-memory ledger kept deliberately small for the runnable example."""

    def __init__(self) -> None:
        self._orders: dict[str, _Order] = {}
        self._events: dict[str, MeteredUsage] = {}
        self._lock = Lock()

    def open_order(self, order_id: str, asset: SellerAsset) -> OrderView:
        with self._lock:
            if order_id in self._orders:
                raise ValueError("order_id already exists")
            self._orders[order_id] = _Order(asset=asset)
            return self._view(order_id)

    def record_buyer_update(self, order_id: str, update: BuyerUpdate) -> MeteredUsage:
        with self._lock:
            existing = self._events.get(update.update_id)
            if existing is not None:
                return existing
            order = self._require_order(order_id)
            if order.handed_off:
                raise ValueError("handed-off orders no longer accept buyer updates")
            if order.buyer_customer_id not in (None, update.buyer_customer_id):
                raise ValueError("buyer_customer_id cannot change during an order")

            order.buyer_customer_id = update.buyer_customer_id
            event = MeteredUsage(
                order_id=order_id,
                customer_id=update.buyer_customer_id,
                source_id=update.update_id,
                kind="buyer_update",
                usage_units=update.usage_units,
            )
            self._events[update.update_id] = event
            order.metered_units += update.usage_units
            return event

    def handoff(self, order_id: str, request: HandoffRequest) -> OrderView:
        with self._lock:
            if request.handoff_id in self._events:
                return self._view(order_id)
            order = self._require_order(order_id)
            if order.buyer_customer_id is None:
                raise ValueError("record a buyer update before handoff")
            order.handed_off = True
            self._events[request.handoff_id] = MeteredUsage(
                order_id=order_id,
                customer_id=order.buyer_customer_id,
                source_id=request.handoff_id,
                kind="order_handoff",
                usage_units=0,
            )
            return self._view(order_id)

    def customer_totals(self) -> dict[str, int]:
        with self._lock:
            totals: dict[str, int] = {}
            for event in self._events.values():
                totals[event.customer_id] = totals.get(event.customer_id, 0) + event.usage_units
            return totals

    def _require_order(self, order_id: str) -> _Order:
        try:
            return self._orders[order_id]
        except KeyError as exc:
            raise ValueError("order_id does not exist") from exc

    def _view(self, order_id: str) -> OrderView:
        order = self._require_order(order_id)
        return OrderView(
            order_id=order_id,
            asset_id=order.asset.asset_id,
            seller_customer_id=order.asset.seller_customer_id,
            buyer_customer_id=order.buyer_customer_id,
            handed_off=order.handed_off,
            metered_units=order.metered_units,
        )

