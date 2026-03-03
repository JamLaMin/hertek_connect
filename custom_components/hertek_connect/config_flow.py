from __future__ import annotations

from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HertekApi
from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_INSTALLATION_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_BASE_URL,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
)


class HertekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._base_url = DEFAULT_BASE_URL
        self._username = ""
        self._password = ""
        self._installations: list[dict] = []

    async def async_step_user(self, user_input=None):
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        self._base_url = user_input[CONF_BASE_URL].rstrip("/")
        self._username = user_input[CONF_USERNAME]
        self._password = user_input[CONF_PASSWORD]

        parsed = urlparse(self._base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_BASE_URL, default=self._base_url): str,
                        vol.Required(CONF_USERNAME, default=self._username): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors={"base": "invalid_base_url"},
            )

        try:
            api = HertekApi(self._base_url, self._username, self._password)
            session = async_get_clientsession(self.hass)
            await api.request_token(session)
            self._installations = await api.get_installations(session)
        except Exception:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_BASE_URL, default=self._base_url): str,
                        vol.Required(CONF_USERNAME, default=self._username): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors={"base": "auth_failed"},
            )

        return await self.async_step_pick_installation()

    async def async_step_pick_installation(self, user_input=None):
        if not self._installations:
            return self.async_abort(reason="no_installations")

        options = {
            str(i["id"]): f'{i.get("name","")}'.strip() or f'Installatie {i["id"]}'
            for i in self._installations
            if "id" in i
        }

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_INSTALLATION_ID): vol.In(options),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=DEFAULT_SCAN_INTERVAL_SECONDS,
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_SECONDS, max=MAX_SCAN_INTERVAL_SECONDS)),
                }
            )
            return self.async_show_form(step_id="pick_installation", data_schema=schema)

        installation_id = int(user_input[CONF_INSTALLATION_ID])
        scan_interval = int(user_input[CONF_SCAN_INTERVAL])

        await self.async_set_unique_id(f"hertek_{installation_id}")
        self._abort_if_unique_id_configured()

        data = {
            CONF_BASE_URL: self._base_url,
            CONF_USERNAME: self._username,
            CONF_PASSWORD: self._password,
            CONF_INSTALLATION_ID: installation_id,
            CONF_SCAN_INTERVAL: scan_interval,
        }

        title = options.get(str(installation_id), f"Hertek {installation_id}")
        return self.async_create_entry(title=title, data=data)

    @callback
    def async_get_options_flow(self, config_entry):
        return HertekOptionsFlowHandler(config_entry)


class HertekOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        current = int(
            self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
            )
        )

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=current,
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL_SECONDS, max=MAX_SCAN_INTERVAL_SECONDS)),
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        return self.async_create_entry(
            title="",
            data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])},
        )
