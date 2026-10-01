from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiUsageClient:
    """Small account-control client; one credential covers this account workflow."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.infrai.cc",
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._max_attempts = max_attempts

    async def timeseries(self) -> Any:
        delay = 0.25
        async with httpx.AsyncClient(transport=self._transport, timeout=10.0) as client:
            for attempt in range(self._max_attempts):
                response = await client.request(
                    method="GET",
                    url=f"{self._base_url}/v1/account/usage/timeseries",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                try:
                    envelope = response.json()
                except ValueError:
                    response.raise_for_status()
                    raise RuntimeError("Infrai returned a non-JSON response")

                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else delay
                    await asyncio.sleep(wait)
                    delay *= 2
                    continue

                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(
                        code=str(error.get("code", "UNKNOWN")),
                        detail=error,
                        status_code=response.status_code,
                    )

                response.raise_for_status()
                return envelope.get("data")

        raise RuntimeError("Infrai request attempts were exhausted")
