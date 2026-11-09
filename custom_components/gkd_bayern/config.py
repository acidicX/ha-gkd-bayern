"""Config entry helpers for the GKD Bayern integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .const import CONF_STATIONS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


def stations_map(entry: ConfigEntry) -> dict[str, dict[str, str]]:
    """Return the configured station mapping, preferring the options value."""
    stations = entry.options.get(CONF_STATIONS)
    if stations is None:
        stations = entry.data.get(CONF_STATIONS)
    return dict(stations or {})


def configured_ids(entry: ConfigEntry) -> list[str]:
    """Return the configured station IDs."""
    return list(stations_map(entry))
