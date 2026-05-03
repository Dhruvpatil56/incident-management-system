from __future__ import annotations

import asyncio
from random import choice

import httpx

COMPONENTS = [("rdbms", "P0"), ("api", "P1"), ("cache", "P2"), ("mcp_host", "P1")]
STATES = ["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"]


async def main() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        for i in range(24):
            comp, sev = choice(COMPONENTS)
            payload = {
                "title": f"Historical incident {i+1}",
                "description": f"Seeded incident for {comp}",
                "source": "seed",
                "root_cause": "Historic root cause data",
                "rca_category": "unknown",
                "rca_description": "Historic remediation notes",
                "component": comp,
                "severity": sev,
                "state": choice(STATES),
            }
            response = await client.post("/api/v1/incidents", json=payload)
            print(i + 1, response.status_code)
            await asyncio.sleep(0.05)


if __name__ == "__main__":
    asyncio.run(main())
