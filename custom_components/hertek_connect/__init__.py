from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .api import HertekApi
from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    SERVICE_REFRESH,
)
from .coordinator import HertekCoordinator

PLATFORMS: list[str] = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    base_url = entry.data[CONF_BASE_URL]
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    installation_id = int(entry.data[CONF_INSTALLATION_ID])
    scan_interval = int(entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))

    api = HertekApi(base_url, username, password)
    coordinator = HertekCoordinator(hass, api, installation_id, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def _handle_refresh(call: ServiceCall) -> None:
        # refresh all entries
        for c in hass.data.get(DOMAIN, {}).values():
            await c.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(DOMAIN, SERVICE_REFRESH, _handle_refresh)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            # last one removed: also remove service
            if hass.services.has_service(DOMAIN, SERVICE_REFRESH):
                hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return unload_ok
