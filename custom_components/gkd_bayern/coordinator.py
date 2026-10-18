"""Coordinator for fetching water temperatures for all configured stations."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    GkdApiClient,
    GkdConnectionError,
    GkdError,
    is_fresh,
    now_berlin,
)
from .const import DOMAIN, UPDATE_INTERVAL
from .data import Measurement, Station

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class GkdDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Measurement | None]]):
    """Fetch the latest measurement for every configured station."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: GkdApiClient,
        stations: dict[str, Station],
        update_interval: timedelta = UPDATE_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._client = client
        self.stations = stations
        # Latest parsed measurement per station, regardless of freshness
        # (used for the last-known-value attributes of the sensors).
        self.last_raw: dict[str, Measurement | None] = {}
        # Last known data situation per station, used to only log when it
        # changes ("fresh", "stale", "empty" or "error").
        self._situations: dict[str, str] = {}

    async def _async_update_data(self) -> dict[str, Measurement | None]:
        """Fetch the latest measurement for every station."""
        now = now_berlin()
        data: dict[str, Measurement | None] = {}
        errors: list[str] = []
        for station_id, station in self.stations.items():
            try:
                measurement = await self._client.get_measurement(station.url)
            except GkdConnectionError as err:
                _LOGGER.warning("Could not update %s: %s", station.name, err)
                self.last_raw[station_id] = None
                data[station_id] = None
                errors.append(station_id)
                _announce(self._situations, station_id, "error", station)
                continue
            self.last_raw[station_id] = measurement
            # A stale measurement (older than one hour) is not used as an
            # update: the sensor entity itself becomes unavailable.
            if measurement is None:
                data[station_id] = None
                _announce(self._situations, station_id, "empty", station)
            elif is_fresh(measurement, now):
                data[station_id] = measurement
                _LOGGER.debug(
                    "%s: current measurement %.1f °C from %s",
                    station.name,
                    measurement.temperature,
                    measurement.measured_at.isoformat(),
                )
                _announce(self._situations, station_id, "fresh", station)
            else:
                data[station_id] = None
                _announce(self._situations, station_id, "stale", station)
        if self.stations and len(errors) == len(self.stations):
            raise UpdateFailed("All station requests failed")
        return data


def _announce(situations: dict[str, str], station_id: str, state: str, station: Station) -> None:
    """Log when a station's data situation changes."""
    if situations.get(station_id) == state:
        return
    situations[station_id] = state
    if state == "fresh":
        _LOGGER.info("%s: current measurement is fresh again", station.name)
    elif state == "stale":
        _LOGGER.info(
            "%s: latest measurement is older than one hour; "
            "the sensor stays unavailable until the GKD publishes a new value",
            station.name,
        )
    elif state == "empty":
        _LOGGER.warning(
            "%s: no measurement row found on the values page "
            "(the GKD website may have changed or has no data)",
            station.name,
        )
    # "error" is already logged on the warning that caused it.


async def create_coordinator(
    hass: HomeAssistant, entry: ConfigEntry, client: GkdApiClient
) -> GkdDataUpdateCoordinator:
    """Build the coordinator for the configured stations of ``entry``."""
    try:
        available = await client.get_stations()
    except GkdError as err:
        raise ConfigEntryNotReady(str(err)) from err

    configured_ids = _configured_ids(entry)
    stations: dict[str, Station] = {}
    for station_id in configured_ids:
        if (station := available.get(station_id)) is not None:
            stations[station_id] = station
            continue
        _LOGGER.warning(
            "Station %s is no longer listed on %s and will not be updated",
            station_id,
            DOMAIN,
        )
    return GkdDataUpdateCoordinator(hass, client, stations)


def _configured_ids(entry: ConfigEntry) -> list[str]:
    """Return configured station IDs from entry options or data."""
    return list(_stations_map(entry))


def _stations_map(entry: ConfigEntry) -> dict[str, dict[str, str]]:
    """Return the raw configured station mapping (options preferred)."""
    merged = dict(entry.data.get("stations") or {})
    merged.update(entry.options.get("stations") or {})
    return merged
