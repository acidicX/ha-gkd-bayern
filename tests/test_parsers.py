"""Tests for the pure parsing helpers of the GKD Bayern integration."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from custom_components.gkd_bayern.api import (
    is_fresh,
    parse_measurement,
    parse_stations,
)
from custom_components.gkd_bayern.const import MAX_AGE

FIXTURES = Path(__file__).parent / "fixtures"
BERLIN = ZoneInfo("Europe/Berlin")


def load(name: str) -> str:
    """Load a HTML fixture."""
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_stations_all_links() -> None:
    """Every station row of the overview is found."""
    stations = parse_stations(load("tabellen.html"))
    assert len(stations) == 153


def test_parse_stations_aug() -> None:
    """A specific station is parsed with all fields."""
    stations = parse_stations(load("tabellen.html"))
    station = stations["12004002"]
    assert station.name == "Augsburg Hochablaß"
    assert station.river == "Lech"
    assert station.district == "A"
    assert station.region == "kelheim"
    assert (
        station.url == "https://www.gkd.bayern.de/de/fluesse/wassertemperatur/"
        "kelheim/augsburg-hochablass-12004002/messwerte?method=tabellen"
    )


def test_parse_measurement() -> None:
    """The newest row of the weekly table is parsed."""
    measurement = parse_measurement(load("messwerte.html"))
    assert measurement is not None
    assert measurement.temperature == 15.1
    assert measurement.measured_at.year == 2026
    assert measurement.measured_at.day == 17
    assert str(measurement.measured_at.tzinfo) == "Europe/Berlin"


def test_parse_measurement_empty_page() -> None:
    """A page without a table yields no measurement."""
    assert parse_measurement("<html><body></body></html>") is None


def test_is_fresh() -> None:
    """Measurements within one hour count as fresh."""
    measurement = parse_measurement(load("messwerte.html"))
    assert measurement is not None
    now = measurement.measured_at
    assert is_fresh(measurement, now) is True
    # inside the one-hour window
    assert is_fresh(measurement, now + MAX_AGE - timedelta(seconds=1)) is True
    # just outside the one-hour window
    assert is_fresh(measurement, now + MAX_AGE + timedelta(seconds=1)) is False
