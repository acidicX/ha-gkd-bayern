"""The GKD Bayern integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GkdApiClient
from .config import configured_ids
from .const import DOMAIN
from .coordinator import GkdBayernConfigEntry, create_coordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: GkdBayernConfigEntry) -> bool:
    """Migrate an old config entry to the current version."""
    if entry.version < 2:
        hass.config_entries.async_update_entry(
            entry,
            unique_id=entry.unique_id or DOMAIN,
            version=2,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GkdBayernConfigEntry) -> bool:
    """Set up the GKD Bayern integration from a config entry."""
    session = async_get_clientsession(hass)
    client = GkdApiClient(hass, session)

    coordinator = await create_coordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    _async_remove_dropped_stations(hass, entry)
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GkdBayernConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: GkdBayernConfigEntry) -> None:
    """Reload the entry when its options change."""
    _async_remove_dropped_stations(hass, entry)
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def _async_remove_dropped_stations(hass: HomeAssistant, entry: GkdBayernConfigEntry) -> None:
    """Remove devices and entities of stations no longer configured."""
    keep_ids = set(configured_ids(entry))
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        station_id = next(
            (value for domain, value in device.identifiers if domain == DOMAIN),
            None,
        )
        if station_id is None or station_id in keep_ids:
            continue
        for entity in er.async_entries_for_device(
            entity_registry, device.id, include_disabled_entities=True
        ):
            entity_registry.async_remove(entity.entity_id)
        device_registry.async_remove_device(device.id)
