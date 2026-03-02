from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity_base import HertekEntityBase
from .helpers import upper


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    installation = coordinator.data.installation
    installation_id = int(installation.get("id"))
    installation_name = installation.get("name") or f"Hertek {installation_id}"

    async_add_entities(
        [
            HertekBrandmeldingActief(coordinator, entry, installation_id, installation_name),
            HertekStoringActief(coordinator, entry, installation_id, installation_name),
            HertekUitgeschakeldActief(coordinator, entry, installation_id, installation_name),
            HertekProbleemActief(coordinator, entry, installation_id, installation_name),
        ],
        update_before_add=True,
    )


def _has_category(alerts: list[dict], category: str) -> bool:
    c = category.upper()
    return any(upper(a.get("statusCategory")) == c for a in alerts)


class HertekBrandmeldingActief(HertekEntityBase, BinarySensorEntity):
    _attr_name = "Brandmelding actief"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_brandmelding_actief"

    @property
    def is_on(self) -> bool:
        return _has_category(self.coordinator.data.alerts or [], "FIRE")


class HertekStoringActief(HertekEntityBase, BinarySensorEntity):
    _attr_name = "Storing actief"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_storing_actief"

    @property
    def is_on(self) -> bool:
        return _has_category(self.coordinator.data.alerts or [], "FAULT")


class HertekUitgeschakeldActief(HertekEntityBase, BinarySensorEntity):
    _attr_name = "Uitgeschakeld actief"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_uitgeschakeld_actief"

    @property
    def is_on(self) -> bool:
        return _has_category(self.coordinator.data.alerts or [], "DISABLEMENT")


class HertekProbleemActief(HertekEntityBase, BinarySensorEntity):
    _attr_name = "Probleem actief"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_probleem_actief"

    @property
    def is_on(self) -> bool:
        alerts = self.coordinator.data.alerts or []
        inst = self.coordinator.data.installation
        conn = upper(inst.get("connectionStatus"))
        if conn and conn != "OK":
            return True
        return len(alerts) > 0
