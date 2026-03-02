from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HertekApi
from .helpers import upper


@dataclass
class HertekData:
    installation: dict[str, Any]
    zones: list[dict[str, Any]]
    alerts: list[dict[str, Any]]


class HertekCoordinator(DataUpdateCoordinator[HertekData]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: HertekApi,
        installation_id: int,
        base_scan_interval_seconds: int,
    ) -> None:
        self.hass = hass
        self.api = api
        self.installation_id = installation_id
        self.session = async_get_clientsession(hass)

        self._base_interval = max(10, int(base_scan_interval_seconds))
        self._failure_count = 0

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Hertek Connect",
            update_interval=timedelta(seconds=self._base_interval),
        )

    def _token_needs_refresh(self) -> bool:
        valid_until = self.api.token_valid_until_utc
        if valid_until is None:
            return True
        now = datetime.now(timezone.utc)
        return now >= (valid_until - timedelta(minutes=5))

    async def _ensure_token(self) -> None:
        if self._token_needs_refresh():
            await self.api.request_token(self.session)

    def _set_interval(self, seconds: int) -> None:
        seconds = max(5, int(seconds))
        self.update_interval = timedelta(seconds=seconds)

    def _adapt_interval_success(self, installation: dict, alerts: list[dict]) -> None:
        # Back to normal first
        interval = self._base_interval

        conn = upper(installation.get("connectionStatus"))
        if conn and conn != "OK":
            # if offline, no need to hammer
            interval = max(interval, 60)

        # Faster when alerts exist
        if alerts:
            interval = min(interval, 15)

            # Even faster when FIRE exists
            if any(upper(a.get("statusCategory")) == "FIRE" for a in alerts):
                interval = min(interval, 10)

        self._set_interval(interval)

    def _backoff_on_failure(self) -> None:
        # exponential backoff: base -> 60 -> 120 -> 300 (max)
        self._failure_count += 1
        if self._failure_count <= 1:
            self._set_interval(max(self._base_interval, 60))
        elif self._failure_count == 2:
            self._set_interval(120)
        else:
            self._set_interval(300)

    async def _async_update_data(self) -> HertekData:
        try:
            await self._ensure_token()

            try:
                installations = await self.api.get_installations(self.session)
            except PermissionError:
                await self.api.request_token(self.session)
                installations = await self.api.get_installations(self.session)

            installation = next(
                (i for i in installations if int(i.get("id", -1)) == int(self.installation_id)),
                None,
            )
            if not installation:
                raise UpdateFailed(f"Installatie id {self.installation_id} niet gevonden.")

            try:
                zones = await self.api.get_zones(self.session, self.installation_id)
                alerts = await self.api.get_alerts(self.session, self.installation_id)
            except PermissionError:
                await self.api.request_token(self.session)
                zones = await self.api.get_zones(self.session, self.installation_id)
                alerts = await self.api.get_alerts(self.session, self.installation_id)

            self._failure_count = 0
            self._adapt_interval_success(installation, alerts or [])

            return HertekData(
                installation=installation,
                zones=zones or [],
                alerts=alerts or [],
            )

        except UpdateFailed:
            self._backoff_on_failure()
            raise
        except Exception as err:
            self._backoff_on_failure()
            raise UpdateFailed(str(err)) from err
