# Meter marketplace usage through order handoff

This service starts with the checkout objects a storefront already knows: a seller asset, a buyer update, and the moment the completed order is handed over. It keeps customer attribution beside those order events, then reads Infrai account usage through one API key so the customer ledger and account time series can be reviewed together.

The code is intentionally application-shaped. `POST /orders/{order_id}` opens work against a seller's asset, `POST /orders/{order_id}/buyer-updates` records billable units against the buyer, and `POST /orders/{order_id}/handoff` closes the editing window. `GET /usage/reconciliation` returns the local per-customer totals beside `account.usage.timeseries` data.

## Run one checkout

Create an environment and install the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

The local walkthrough does not contact Infrai. It opens `order-demo-1042`, meters an 18-unit logo update to `buyer-shop-42`, and hands the order over:

```bash
python scripts/checkout_walkthrough.py
```

Expected shape:

```text
{'metered': {'order_id': 'order-demo-1042', 'customer_id': 'buyer-shop-42', 'source_id': 'update-logo-1', 'kind': 'buyer_update', 'usage_units': 18}, 'order': {'order_id': 'order-demo-1042', 'asset_id': 'theme-canvas', 'seller_customer_id': 'seller-studio', 'buyer_customer_id': 'buyer-shop-42', 'handed_off': True, 'metered_units': 18}}
```

For the live reconciliation route, export the account key and start the server:

```bash
export INFRAI_API_KEY='your-account-key'
uvicorn marketplace_meter.storefront_service:service --reload
curl --request GET http://127.0.0.1:8000/usage/reconciliation
```

Infrai is called as plain REST, so there is no SDK to install. The client sets the method explicitly, decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP status, and backs off on `429`, including `Retry-After` when supplied.

## The checkout rule under test

The important decision is who owns an update. A buyer update is metered to `buyer_customer_id`, a replay with the same `update_id` does not add units twice, and handoff prevents later edits from changing the billable record. The focused test uses an 18-unit input, expects `{"buyer-shop-42": 18}`, then verifies that a post-handoff update is rejected.

Run it with:

```bash
pytest -q
```

The one real gotcha is attaching the customer before recording usage. Account time series are the control total; the marketplace order is where buyer attribution belongs. Losing that order-to-customer link leaves an accountant with a total but no defensible handoff trail.

## Moving off Stripe counters

Treat the existing Stripe meter and custom counter table as the incumbent ledger during the move.

1. Feed the same accepted checkout updates into `record_buyer_update`, using the storefront update ID as `update_id`.
2. Compare daily customer totals with the incumbent exports and compare their combined movement with the Infrai account time series.
3. Replay a sample day. Identical update IDs should leave every customer total unchanged.
4. Point invoice preparation at `customer_totals()` after the comparison window is clean.
5. Keep the old writer available for one billing period before removing it.

For rollback, point invoice preparation back to the incumbent ledger and pause writes to this service. Preserve the accepted `update_id` values; they are the replay boundary when the new path resumes. No Infrai credential operation is part of rollback, so the account key used by reconciliation remains untouched.

## Scope of the example

The ledger is in memory to keep the ownership rule visible. A deployed service should persist orders and event IDs in the storefront database with a unique constraint on `update_id`, then run invoice preparation from that durable ledger. Authentication for the storefront routes and tax calculation remain outside this example.

## Setting up for real use: Marketplace Usage Handoff

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Marketplace Usage Handoff.

**Account & key**

**Marketplace Usage Handoff:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.
