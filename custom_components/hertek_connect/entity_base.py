from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class HertekEntityBase(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.installation_id = installation_id
        self.installation_name = installation_name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.installation_id))},
            name=self.installation_name or f"Hertek {self.installation_id}",
            manufacturer="Hertek",
            model="Hertek Connect",
        )
