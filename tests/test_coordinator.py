"""Tests for the coordinator: adaptive retry interval and logging."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from unittest.mock import MagicMock

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed
import pytest

from custom_components.gkd_bayern.api import GkdConnectionError, now_berlin
from custom_components.gkd_bayern.const import UPDATE_INTERVAL
from custom_components.gkd_bayern.coordinator import (
    RETRY_INTERVAL,
    GkdDataUpdateCoordinator,
    _announce,
    create_coordinator,
)
from custom_components.gkd_bayern.data import Measurement, Station

STATIONS = {
    "s1": Station("s1", "Alpha", "River", "District", "/de/x/alpha-1/messwerte"),
    "s2": Station("s2", "Beta", "River", "District", "/de/x/beta-2/messwerte"),
}

ZONE = now_berlin()


def fresh_measurement() -> Measurement:
    """Return a current measurement (well within the one-hour rule)."""
    return Measurement(14.0, ZONE - timedelta(minutes=5))


class StubClient:
    """Client stub returning the same result for every station."""

    def __init__(self, result):
        self.result = result

    async def get_measurement(self, url):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make_coordinator(result) -> GkdDataUpdateCoordinator:
    """Build a real coordinator with a stubbed hass and client."""
    entry = MagicMock()
    entry.data = {"stations": {}}
    entry.options = {}
    return GkdDataUpdateCoordinator(
        MagicMock(),
        StubClient(result),
        dict(STATIONS),
        config_entry=entry,
    )


def update(coordinator) -> dict:
    """Run one update cycle."""
    return asyncio.run(coordinator._async_update_data())


def test_backoff_doubles_then_caps() -> None:
    """Unhealthy cycles retry after 30 s, 60 s, ... capped at the interval."""
    coordinator = make_coordinator(None)
    expected = [
        30,
        60,
        120,
        240,
        480,
        UPDATE_INTERVAL.total_seconds(),
        UPDATE_INTERVAL.total_seconds(),
    ]
    for cycle, seconds in enumerate(expected, start=1):
        update(coordinator)
        assert coordinator.update_interval == timedelta(seconds=seconds), cycle
        assert coordinator._unhealthy_cycles == cycle


def test_backoff_resets_when_fresh() -> None:
    """One fresh cycle restores the normal interval and clears the counter."""
    coordinator = make_coordinator(None)
    update(coordinator)
    update(coordinator)
    coordinator._client = StubClient(fresh_measurement())
    data = update(coordinator)
    assert all(value is not None for value in data.values())
    assert coordinator.update_interval == UPDATE_INTERVAL
    assert coordinator._unhealthy_cycles == 0


def test_partial_health_is_unhealthy() -> None:
    """A cycle where only some stations have data keeps the backoff."""
    measurement = fresh_measurement()

    class MixedClient:
        async def get_measurement(self, url):
            if "alpha" in url:
                return measurement
            return None

    coordinator = GkdDataUpdateCoordinator(MagicMock(), MixedClient(), dict(STATIONS))
    data = update(coordinator)
    assert data["s1"] is not None
    assert data["s2"] is None
    assert coordinator.update_interval == RETRY_INTERVAL
    assert coordinator._unhealthy_cycles == 1


def test_all_failed_raises_update_failed() -> None:
    """If every station request errors, the update raises UpdateFailed."""
    coordinator = make_coordinator(GkdConnectionError("boom"))
    with pytest.raises(UpdateFailed):
        update(coordinator)


def test_announce_logs_only_situation_changes(caplog) -> None:
    """Transitions are logged, repeats are not."""
    situations: dict[str, str] = {}
    with caplog.at_level(logging.DEBUG, logger="custom_components.gkd_bayern.coordinator"):
        _announce(situations, "s1", "empty", STATIONS["s1"], 1)
        _announce(situations, "s1", "empty", STATIONS["s1"], 2)
        _announce(situations, "s1", "fresh", STATIONS["s1"], 0)
    messages = [record.message for record in caplog.records]
    assert len(messages) == 2
    assert "no measurement row found" in messages[0]
    assert "fresh again" in messages[1]


def test_create_coordinator_raises_on_connection_error() -> None:
    """A failing station overview makes the entry setup retry."""
    entry = MagicMock()
    entry.data = {"stations": {"s1": {}}}
    entry.options = {}

    class BrokenClient:
        async def get_stations(self):
            raise GkdConnectionError("offline")

    with pytest.raises(ConfigEntryNotReady):
        asyncio.run(create_coordinator(MagicMock(), entry, BrokenClient()))


def test_create_coordinator_raises_on_empty_overview() -> None:
    """An empty overview means the site changed; the setup retries."""
    entry = MagicMock()
    entry.data = {"stations": {"s1": {}}}
    entry.options = {}

    class EmptyClient:
        async def get_stations(self):
            return {}

    with pytest.raises(ConfigEntryNotReady):
        asyncio.run(create_coordinator(MagicMock(), entry, EmptyClient()))


def test_create_coordinator_filters_unknown_stations(caplog) -> None:
    """Only stations still listed on the website are updated."""
    entry = MagicMock()
    entry.data = {"stations": {"s1": {}, "gone": {}}}
    entry.options = {}

    class OkClient:
        async def get_stations(self):
            return dict(STATIONS)

    coordinator = asyncio.run(create_coordinator(MagicMock(), entry, OkClient()))
    assert list(coordinator.stations) == ["s1"]
    assert any("gone" in record.message for record in caplog.records)
