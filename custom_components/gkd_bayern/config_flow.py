"""Config flow to set up the GKD Bayern integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .api import GkdApiClient, GkdError
from .config import stations_map
from .const import CONF_STATIONS, DOMAIN, NAME, TABLES_URL

_LOGGER = logging.getLogger(__name__)


async def _fetch_stations(hass: HomeAssistant) -> dict[str, dict[str, str]]:
    """Fetch all available stations (as stored config dicts)."""
    client = GkdApiClient(hass, async_get_clientsession(hass))
    raw = await client.get_stations()
    return {sid: s.as_config() for sid, s in raw.items()}


def _station_options(stations: dict[str, dict[str, str]]) -> dict[str, str]:
    """Return selectable options sorted by station name."""
    options = {sid: f"{station['name']} ({station['river']})" for sid, station in stations.items()}
    return dict(sorted(options.items(), key=lambda item: item[1].lower()))


class GkdConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the GKD Bayern config flow."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the integration entry with the initially selected stations."""
        # The station list is maintained in the options flow, so allow only
        # a single config entry.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured(error="single_instance_allowed")

        try:
            stations = await _fetch_stations(self.hass)
        except GkdError as err:
            _LOGGER.debug("Could not load the station list: %s", err)
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({vol.Required("selected", default=[]): cv.multi_select({})}),
                errors={"base": "cannot_connect"},
                description_placeholders={"station_list_url": TABLES_URL},
            )

        errors: dict[str, str] = {}
        if user_input is not None:
            selected: list[str] = user_input["selected"]
            if not selected:
                errors["base"] = "no_stations"
            elif missing := [sid for sid in selected if sid not in stations]:
                _LOGGER.debug("Selected stations are no longer listed: %s", missing)
                errors["base"] = "station_not_found"
            else:
                return self.async_create_entry(
                    title=NAME,
                    data={CONF_STATIONS: {sid: stations[sid] for sid in selected}},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("selected", default=[]): cv.multi_select(_station_options(stations))}
            ),
            errors=errors,
            description_placeholders={"station_list_url": TABLES_URL},
        )


class GkdOptionsFlow(config_entries.OptionsFlow):
    """Options flow to add or remove configured stations."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the station list."""
        entry = self.config_entry
        current: dict[str, dict[str, str]] = stations_map(entry)
        current_labels = _station_options(current)
        # Stations that vanished from the GKD overview keep their label.
        labels = {**current_labels}

        try:
            available = await _fetch_stations(self.hass)
        except GkdError as err:
            _LOGGER.debug("Could not load the station list: %s", err)
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {vol.Required("selected", default=list(current)): cv.multi_select(labels)}
                ),
                errors={"base": "cannot_connect"},
            )

        labels.update(_station_options(available))
        labels = dict(sorted(labels.items(), key=lambda item: item[1].lower()))

        errors: dict[str, str] = {}
        if user_input is not None:
            selected: list[str] = user_input["selected"]
            if not selected:
                errors["base"] = "no_stations"
            elif missing := [
                sid for sid in selected if sid not in available and sid not in current
            ]:
                _LOGGER.debug("Selected stations are no longer listed: %s", missing)
                errors["base"] = "station_not_found"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_STATIONS: {sid: available.get(sid) or current[sid] for sid in selected}
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required("selected", default=list(current)): cv.multi_select(labels)}
            ),
            errors=errors,
        )
