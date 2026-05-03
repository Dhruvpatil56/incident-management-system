from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from observability.prometheus import db_timing
from signals.models import Signal
from signals.retry import with_async_retry


class SignalStore:
    def __init__(self, collection):
        self.collection = collection

    async def insert(self, signal: Signal) -> Signal:
        with db_timing("mongo", "insert_signal"):
            await with_async_retry(
                lambda: self.collection.insert_one(signal.model_dump(mode="json")),
                db="mongo",
                operation="insert_signal",
            )
        return signal

    async def insert_many(self, signals: Sequence[Signal]) -> int:
        if not signals:
            return 0
        payload = [signal.model_dump(mode="json") for signal in signals]
        with db_timing("mongo", "insert_many_signals"):
            result = await with_async_retry(
                lambda: self.collection.insert_many(payload),
                db="mongo",
                operation="insert_many_signals",
            )
        return len(result.inserted_ids)

    async def find_by_component(self, component_id: str) -> list[Signal]:
        with db_timing("mongo", "find_by_component"):
            docs = await self.collection.find({"component_id": component_id}).to_list(1000)
        return [Signal(**doc) for doc in docs]

    async def find_by_work_item(self, work_item_id: UUID) -> list[Signal]:
        with db_timing("mongo", "find_by_work_item"):
            docs = await self.collection.find({"work_item_id": str(work_item_id)}).to_list(1000)
        return [Signal(**doc) for doc in docs]

    async def count_by_component(self, component_id: str) -> int:
        with db_timing("mongo", "count_by_component"):
            return int(await self.collection.count_documents({"component_id": component_id}))


class InMemorySignalStore:
    def __init__(self):
        self._records: list[Signal] = []

    async def insert(self, signal: Signal) -> Signal:
        self._records.append(signal)
        return signal

    async def insert_many(self, signals: Sequence[Signal]) -> int:
        self._records.extend(signals)
        return len(signals)

    async def find_by_component(self, component_id: str) -> list[Signal]:
        return [s for s in self._records if s.component_id == component_id]

    async def find_by_work_item(self, work_item_id: UUID) -> list[Signal]:
        return [s for s in self._records if s.work_item_id == work_item_id]

    async def count_by_component(self, component_id: str) -> int:
        return len([s for s in self._records if s.component_id == component_id])
