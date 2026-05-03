from __future__ import annotations

import asyncio

import httpx

SCENARIOS = [
    {"component_id": "db-primary", "component_type": "rdbms", "severity": "P0"},
    {"component_id": "cache-redis", "component_type": "cache", "severity": "P2"},
    {"component_id": "api-gateway", "component_type": "api", "severity": "P1"},
    {"component_id": "mcp-host-1", "component_type": "mcp_host", "severity": "P1"},
]


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        for scenario in SCENARIOS:
            payload = {
                **scenario,
                "raw_payload": {"event": "simulated_failure"},
            }
            response = await client.post("/api/v1/signals", json=payload)
            print(scenario["component_type"], response.status_code, response.text)
            await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
