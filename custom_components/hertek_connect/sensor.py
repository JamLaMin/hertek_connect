from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import STATE_UNKNOWN

from .const import (
    DOMAIN,
    STATUSCATEGORY_NL,
    CONNECTIONSTATUS_NL,
    DEVICETYPE_NL,
)
from .entity_base import HertekEntityBase
from .helpers import parse_dt, upper


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
            HertekHoofdstatusSensor(coordinator, entry, installation_id, installation_name),
            HertekVerbindingSensor(coordinator, entry, installation_id, installation_name),
            HertekActieveMeldingenSensor(coordinator, entry, installation_id, installation_name),
            HertekLaatsteMeldingSensor(coordinator, entry, installation_id, installation_name),

            # diagnostic
            HertekLaatsteCheckinSensor(coordinator, entry, installation_id, installation_name),
            HertekInstallatieStatusRawSensor(coordinator, entry, installation_id, installation_name),
            HertekLaatsteMeldingZoneNummerSensor(coordinator, entry, installation_id, installation_name),
            HertekLaatsteMeldingZoneNaamSensor(coordinator, entry, installation_id, installation_name),
        ],
        update_before_add=True,
    )


def _zone_lookup(zones: list[dict], zone_id: int | None) -> dict | None:
    if zone_id is None:
        return None
    return next((z for z in zones if z.get("id") == zone_id), None)


def _has_category(alerts: list[dict], category: str) -> bool:
    c = category.upper()
    return any(upper(a.get("statusCategory")) == c for a in alerts)


class HertekHoofdstatusSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Hoofdstatus"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_hoofdstatus"

    @property
    def native_value(self):
        inst = self.coordinator.data.installation
        alerts = self.coordinator.data.alerts or []

        conn = upper(inst.get("connectionStatus"))
        if conn and conn != "OK":
            return "Offline"

        if _has_category(alerts, "FIRE"):
            return "Brandmelding"
        if _has_category(alerts, "FAULT"):
            return "Storing"
        if _has_category(alerts, "DISABLEMENT"):
            return "Uitgeschakeld"

        sc = upper(inst.get("statusCategory")) or "UNKNOWN"
        return STATUSCATEGORY_NL.get(sc, "Onbekend")


class HertekVerbindingSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Verbinding"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_verbinding"

    @property
    def native_value(self):
        raw = upper(self.coordinator.data.installation.get("connectionStatus")) or "UNKNOWN"
        return CONNECTIONSTATUS_NL.get(raw, raw)


class HertekActieveMeldingenSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Actieve meldingen"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "meldingen"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_actieve_meldingen"

    @property
    def native_value(self):
        return len(self.coordinator.data.alerts or [])

    @property
    def extra_state_attributes(self):
        alerts = self.coordinator.data.alerts or []
        return {"alerts_top5": alerts[:5]}


class HertekLaatsteMeldingSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Laatste melding"

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_laatste_melding"

    @property
    def native_value(self):
        alerts = self.coordinator.data.alerts or []
        if not alerts:
            return "Geen actieve meldingen"

        a = alerts[0]
        status_category = upper(a.get("statusCategory")) or "UNKNOWN"

        zone_id = a.get("zoneId")
        z = _zone_lookup(self.coordinator.data.zones or [], zone_id)

        zone_txt = "Zone onbekend"
        if z and z.get("number") is not None:
            zone_txt = f"Zone {z.get('number')}"
            if z.get("name"):
                zone_txt += f" {z.get('name')}"

        device_type_raw = upper(a.get("deviceType"))
        device_nl = DEVICETYPE_NL.get(device_type_raw, a.get("deviceType") or "Onbekend")

        name = a.get("name") or "Onbekend"

        if status_category == "DISABLEMENT":
            actie = "Uitgeschakeld"
        elif status_category == "FIRE":
            actie = "Brandmelding"
        elif status_category == "FAULT":
            actie = "Storing"
        else:
            actie = STATUSCATEGORY_NL.get(status_category, "Afwijking")

        lus = a.get("loop")
        adres = a.get("address")

        extra = []
        if lus is not None:
            extra.append(f"Lus {lus}")
        if adres is not None:
            extra.append(f"Adres {adres}")

        extra_txt = ", ".join(extra)
        extra_txt = f" ({extra_txt})" if extra_txt else ""

        return f"{zone_txt}. {device_nl} {name}. {actie}.{extra_txt}"

    @property
    def extra_state_attributes(self):
        alerts = self.coordinator.data.alerts or []
        return {"raw": alerts[0]} if alerts else {}


# Diagnostics

class HertekLaatsteCheckinSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Laatste check-in"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_laatste_checkin"

    @property
    def native_value(self):
        nodes = self.coordinator.data.installation.get("nodes") or []
        if not nodes:
            return None
        return parse_dt(nodes[0].get("lastCheckinAt"))


class HertekInstallatieStatusRawSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Installatie status (raw)"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_status_raw"

    @property
    def native_value(self):
        return self.coordinator.data.installation.get("statusCategory") or STATE_UNKNOWN


class HertekLaatsteMeldingZoneNummerSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Laatste melding zone nummer"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_laatste_zone_nummer"

    @property
    def native_value(self):
        alerts = self.coordinator.data.alerts or []
        if not alerts:
            return None
        z = _zone_lookup(self.coordinator.data.zones or [], alerts[0].get("zoneId"))
        return z.get("number") if z else None


class HertekLaatsteMeldingZoneNaamSensor(HertekEntityBase, SensorEntity):
    _attr_name = "Laatste melding zone naam"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, installation_id: int, installation_name: str) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self._attr_unique_id = f"{installation_id}_laatste_zone_naam"

    @property
    def native_value(self):
        alerts = self.coordinator.data.alerts or []
        if not alerts:
            return None
        z = _zone_lookup(self.coordinator.data.zones or [], alerts[0].get("zoneId"))
        return z.get("name") if z else None
