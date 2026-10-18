"""Shared entity features for the GKD Bayern integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import GkdDataUpdateCoordinator
from .data import Station


class GkdEntity(CoordinatorEntity[GkdDataUpdateCoordinator], Entity):
    """Base entity for the GKD Bayern integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GkdDataUpdateCoordinator,
        station: Station,
        unique_id: str,
    ) -> None:
        """Initialize the entity for a station."""
        super().__init__(coordinator)
        self._station = station
        self._attr_unique_id = unique_id
        self.station_id = station.id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, station.id)},
            name=station.name,
            manufacturer=MANUFACTURER,
            model=f"Wassertemperatur ({station.river})",
            configuration_url=station.url,
        )
