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
                continue
            # A stale measurement (older than one hour) is not used as an
            # update: the sensor entity itself becomes unavailable.
            self.last_raw[station_id] = measurement
            data[station_id] = measurement if is_fresh(measurement, now) else None
        if self.stations and len(errors) == len(self.stations):
            raise UpdateFailed("All station requests failed")
        return data


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
