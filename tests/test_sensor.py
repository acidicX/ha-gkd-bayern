"""Regression tests for the sensor entity available-state logic."""

from __future__ import annotations

from custom_components.gkd_bayern.data import Measurement, Station
from custom_components.gkd_bayern.sensor import GkdWaterTemperatureSensor

STATION = Station(
    id="12004002",
    name="Augsburg Hochablaß",
    river="Lech",
    district="A",
    url=(
        "https://www.gkd.bayern.de/de/fluesse/wassertemperatur/"
        "kelheim/augsburg-hochablass-12004002/messwerte?method=tabellen"
    ),
)
MEASUREMENT = Measurement(temperature=15.0, measured_at=None)  # type: ignore[arg-type]


class FakeCoordinator:
    """Duck-typed stand-in for GkdDataUpdateCoordinator (no hass needed)."""

    def __init__(
        self,
        data: dict,
        last_raw: dict | None = None,
        last_update_success: bool = True,
    ) -> None:
        self.data = data
        self.last_raw = last_raw or {}
        self.last_update_success = last_update_success


def build_sensor(coordinator) -> GkdWaterTemperatureSensor:
    """Create a sensor for the sample station."""
    return GkdWaterTemperatureSensor(coordinator, STATION)  # type: ignore[arg-type]


def test_available_with_fresh_data() -> None:
    """A fresh measurement makes the sensor available."""
    sensor = build_sensor(FakeCoordinator({STATION.id: MEASUREMENT}))
    assert sensor.available is True


def test_unavailable_when_stale() -> None:
    """No data entry (stale measurement) means unavailable."""
    sensor = build_sensor(FakeCoordinator({STATION.id: None}))
    assert sensor.available is False


def test_unavailable_when_missing() -> None:
    """An untracked station id means unavailable, not a crash."""
    sensor = build_sensor(FakeCoordinator({}))
    assert sensor.available is False


def test_unavailable_when_update_failed() -> None:
    """A failed coordinator refresh makes the sensor unavailable."""
    sensor = build_sensor(
        FakeCoordinator(
            {STATION.id: MEASUREMENT},
            last_update_success=False,
        )
    )
    assert sensor.available is False


def test_available_reads_coordinator_success_flag() -> None:
    """`last_update_success` is a coordinator attribute in current HA.

    Regression guard: the managed-entity attribute of older HA versions
    was removed; reading `self.last_update_success` on the entity raises
    AttributeError at state write time.
    """
    sensor = build_sensor(FakeCoordinator({STATION.id: MEASUREMENT}))
    assert not hasattr(sensor, "last_update_success")
    assert sensor.available is True
