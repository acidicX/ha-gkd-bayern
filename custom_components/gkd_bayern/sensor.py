"""Water temperature sensors for the GKD Bayern integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_DISTRICT,
    ATTR_LAST_MEASURED_AT,
    ATTR_LAST_VALUE,
    ATTR_MEASURED_AT,
    ATTR_REGION,
    ATTR_RIVER,
    ATTR_STATION_ID,
    ATTR_URL,
    ATTRIBUTION,
    ATTRIBUTION_TEXT,
    DOMAIN,
)
from .entity import GkdEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from .coordinator import GkdDataUpdateCoordinator
    from .data import Measurement, Station


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a sensor per configured station."""
    coordinator: GkdDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        GkdWaterTemperatureSensor(coordinator, station) for station in coordinator.stations.values()
    )


class GkdWaterTemperatureSensor(GkdEntity, SensorEntity):
    """Current water temperature of a GKD Bayern station."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_name = None
    _attr_translation_key = "water_temperature"

    def __init__(self, coordinator: GkdDataUpdateCoordinator, station: Station) -> None:
        """Initialize the sensor for a station."""
        super().__init__(coordinator, station, unique_id=f"{DOMAIN}_{station.id}")
        # The coordinator's first refresh has already run when the sensor
        # platform is set up, so seed the state from existing data instead
        # of waiting for the next refresh cycle.
        self._last_fresh: Measurement | None = coordinator.data.get(station.id)
        self._attr_native_value: float | None = self._initial_value()

    @property
    def available(self) -> bool:
        """Stale or failed data makes the sensor unavailable."""
        return self.coordinator.last_update_success and (
            self.coordinator.data.get(self.station_id) is not None
        )

    def _initial_value(self) -> float | None:
        """Evaluate the current value from coordinator data."""
        measurement = self.coordinator.data.get(self.station_id)
        if measurement is not None:
            # The coordinator already filtered out stale (> 1 h) values.
            self._last_fresh = measurement
            return measurement.temperature
        return None

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes with station details."""
        attributes = {
            ATTR_STATION_ID: self._station.id,
            ATTR_RIVER: self._station.river,
            ATTR_DISTRICT: self._station.district,
            ATTR_REGION: self._station.region,
            ATTR_URL: self._station.url,
            ATTRIBUTION: ATTRIBUTION_TEXT,
        }
        last = self.coordinator.last_raw.get(self.station_id)
        if last is not None:
            attributes[ATTR_LAST_MEASURED_AT] = last.measured_at.isoformat()
            attributes[ATTR_LAST_VALUE] = last.temperature
        if self._last_fresh is not None:
            attributes[ATTR_MEASURED_AT] = self._last_fresh.measured_at.isoformat()
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle new measurement data."""
        self._attr_native_value = self._initial_value()
        self.async_write_ha_state()
