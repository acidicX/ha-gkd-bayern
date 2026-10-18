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
from .const import DOMAIN, TABLES_URL

_LOGGER = logging.getLogger(__name__)


async def _fetch_stations(hass: HomeAssistant) -> dict[str, dict[str, str]]:
    """Fetch all available stations (as stored config dicts)."""
    client = GkdApiClient(async_get_clientsession(hass))
    raw = await client.get_stations()
    return {sid: s.as_config() for sid, s in raw.items()}


def _station_options(stations: dict[str, dict[str, str]]) -> dict[str, str]:
    """Return selectable options sorted by station name."""
    options = {sid: f"{station['name']} ({station['river']})" for sid, station in stations.items()}
    return dict(sorted(options.items(), key=lambda item: item[1].lower()))


class GkdConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the GKD Bayern config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the integration entry with the initially selected stations."""
        errors: dict[str, str] = {}

        # The station list is maintained in the options flow, so allow only
        # a single config entry.
        source_ignore = config_entries.SOURCE_IGNORE
        if any(
            entry.domain == DOMAIN and entry.source != source_ignore
            for entry in self.hass.config_entries.async_entries()
        ):
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            selected: list[str] = user_input["selected"]
            if not selected:
                errors["base"] = "no_stations"
            else:
                try:
                    stations = await _fetch_stations(self.hass)
                except GkdError as err:
                    _LOGGER.debug("Could not load the station list: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    stations_map = {sid: stations[sid] for sid in selected}
                    return self.async_create_entry(
                        title="GKD Bayern Wassertemperatur",
                        data={"stations": stations_map},
                    )

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
        current: dict[str, dict[str, str]] = entry.data.get("stations", {})
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

        if user_input is not None:
            selected: list[str] = user_input["selected"]
            if not selected:
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema(
                        {vol.Required("selected", default=list(current)): cv.multi_select(labels)}
                    ),
                    errors={"base": "no_stations"},
                )
            stations_map = {sid: available.get(sid) or current[sid] for sid in selected}
            return self.async_create_entry(title="", data={"stations": stations_map})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required("selected", default=list(current)): cv.multi_select(labels)}
            ),
        )
