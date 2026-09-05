"""Unit tests for durable webhook idempotency (H2).

Seam: IdempotencyStore.seen / IdempotencyStore.mark on an injected db_path.
Stores event ids only — no payloads.
"""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_duplicate_mark_within_one_process_is_single_effect(tmp_path):
    """A second mark of the same event_id in one store does not change seen."""
    from src.services.idempotency import IdempotencyStore

    store = IdempotencyStore(tmp_path / "idem.db")
    event_id = "evt-one-process"

    assert await store.seen(event_id) is False
    await store.mark(event_id)
    assert await store.seen(event_id) is True
    await store.mark(event_id)
    assert await store.seen(event_id) is True


@pytest.mark.asyncio
async def test_restart_fresh_store_on_same_db_still_dedupes(tmp_path):
    """H2: a new IdempotencyStore on the same DB file still sees prior marks."""
    from src.services.idempotency import IdempotencyStore

    db = tmp_path / "idem-restart.db"
    event_id = "evt-after-restart"

    first_process = IdempotencyStore(db)
    await first_process.mark(event_id)
    assert await first_process.seen(event_id) is True

    restarted = IdempotencyStore(db)
    assert restarted is not first_process
    assert await restarted.seen(event_id) is True


@pytest.mark.asyncio
async def test_two_store_instances_on_same_db_dedupe(tmp_path):
    """H2: two workers sharing one DB file agree on seen event ids."""
    from src.services.idempotency import IdempotencyStore

    db = tmp_path / "idem-workers.db"
    event_id = "evt-shared-workers"

    worker_a = IdempotencyStore(db)
    worker_b = IdempotencyStore(db)
    await worker_a.mark(event_id)

    assert await worker_b.seen(event_id) is True
    await worker_b.mark(event_id)
    assert await worker_a.seen(event_id) is True


@pytest.mark.asyncio
async def test_unique_constraint_race_second_insert_absorbed(tmp_path):
    """Concurrent marks of the same event_id must not raise (no 500)."""
    from src.services.idempotency import IdempotencyStore

    db = tmp_path / "idem-race.db"
    event_id = "evt-race"
    worker_a = IdempotencyStore(db)
    worker_b = IdempotencyStore(db)

    results = await asyncio.gather(
        worker_a.mark(event_id),
        worker_b.mark(event_id),
        return_exceptions=True,
    )
    for result in results:
        assert not isinstance(result, BaseException)

    assert await worker_a.seen(event_id) is True
    assert await worker_b.seen(event_id) is True
