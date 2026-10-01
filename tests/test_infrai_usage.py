import asyncio

import httpx

from marketplace_meter.infrai_usage import InfraiUsageClient


def test_timeseries_decodes_success_envelope() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/v1/account/usage/timeseries"
        assert request.headers["Authorization"] == "Bearer test-key-from-fixture"
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"period": "current", "points": []},
                "error": None,
                "metadata": {},
            },
        )

    client = InfraiUsageClient(
        "test-key-from-fixture",
        transport=httpx.MockTransport(handler),
    )

    assert asyncio.run(client.timeseries()) == {"period": "current", "points": []}

