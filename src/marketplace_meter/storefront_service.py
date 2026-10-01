from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException

from .infrai_usage import InfraiError, InfraiUsageClient
from .order_handoff import BuyerUpdate, HandoffRequest, OrderLedger, OrderView, SellerAsset

service = FastAPI(title="Marketplace usage handoff")
ledger = OrderLedger()


@service.post("/orders/{order_id}", response_model=OrderView, status_code=201)
def open_order(order_id: str, asset: SellerAsset) -> OrderView:
    try:
        return ledger.open_order(order_id, asset)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@service.post("/orders/{order_id}/buyer-updates")
def record_buyer_update(order_id: str, update: BuyerUpdate) -> dict[str, Any]:
    try:
        event = ledger.record_buyer_update(order_id, update)
        return {"metered": event.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@service.post("/orders/{order_id}/handoff", response_model=OrderView)
def handoff_order(order_id: str, request: HandoffRequest) -> OrderView:
    try:
        return ledger.handoff(order_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@service.get("/usage/reconciliation")
async def usage_reconciliation() -> dict[str, Any]:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")
    try:
        account_timeseries = await InfraiUsageClient(api_key).timeseries()
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail=exc.detail) from exc
    except (RuntimeError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "customer_totals": ledger.customer_totals(),
        "account_timeseries": account_timeseries,
    }

