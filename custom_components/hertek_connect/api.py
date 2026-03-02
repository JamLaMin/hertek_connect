from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import PATH_ALERTS, PATH_INSTALLATIONS, PATH_REQUEST_TOKEN, PATH_ZONES
from .helpers import parse_dt


@dataclass
class HertekToken:
    token: str
    valid_until_utc: Any  # datetime | None


class HertekApi:
    def __init__(self, base_url: str, username: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._token: str | None = None
        self._valid_until_utc = None

    @property
    def token_valid_until_utc(self):
        return self._valid_until_utc

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def request_token(self, session: aiohttp.ClientSession) -> HertekToken:
        url = self._url(PATH_REQUEST_TOKEN)
        payload = {"username": self.username, "password": self.password}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"Token request failed HTTP {resp.status}: {text}")
            data = await resp.json()

        token = data.get("token")
        valid_until = parse_dt(data.get("validUntil"))
        if not token:
            raise RuntimeError("Token response missing 'token'")

        self._token = token
        self._valid_until_utc = valid_until
        return HertekToken(token=token, valid_until_utc=valid_until)

    async def _get_json(self, session: aiohttp.ClientSession, url: str) -> Any:
        async with session.get(url, headers=self._auth_headers(), timeout=aiohttp.ClientTimeout(total=20)) as resp:
            if resp.status == 401:
                raise PermissionError("Unauthorized (401)")
            text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"GET failed HTTP {resp.status}: {text}")
            if not text:
                return None
            return await resp.json()

    async def get_installations(self, session: aiohttp.ClientSession) -> list[dict]:
        return await self._get_json(session, self._url(PATH_INSTALLATIONS)) or []

    async def get_zones(self, session: aiohttp.ClientSession, installation_id: int) -> list[dict]:
        path = PATH_ZONES.format(installationId=installation_id)
        return await self._get_json(session, self._url(path)) or []

    async def get_alerts(self, session: aiohttp.ClientSession, installation_id: int) -> list[dict]:
        path = PATH_ALERTS.format(installationId=installation_id)
        return await self._get_json(session, self._url(path)) or []
