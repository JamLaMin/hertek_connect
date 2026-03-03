from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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

    zone_entities = []
    for zone in coordinator.data.zones or []:
        zone_id = zone.get("id")
        if zone_id is None:
            continue
        zone_entities.append(
            HertekZoneStatusSensor(
                coordinator,
                entry,
                installation_id,
                installation_name,
                int(zone_id),
            )
        )

    device_entities = []
    for device in _collect_devices_from_zones(coordinator.data.zones or []):
        device_entities.append(
            HertekDeviceStatusSensor(
                coordinator,
                entry,
                installation_id,
                installation_name,
                device,
            )
        )

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
            *zone_entities,
            *device_entities,
        ],
        update_before_add=True,
    )

    known_device_keys: set[str] = set()

    @callback
    def _async_add_new_device_entities() -> None:
        new_entities = []
        for device in _collect_devices_from_zones(coordinator.data.zones or []):
            key = _device_unique_key(device, device.get("zoneId"))
            if not key or key in known_device_keys:
                continue
            known_device_keys.add(key)
            new_entities.append(
                HertekDeviceStatusSensor(
                    coordinator,
                    entry,
                    installation_id,
                    installation_name,
                    device,
                )
            )

        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_device_entities()
    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_device_entities))




    # Dynamische element-sensors (melders / sirenes / modules)
    elements = getattr(coordinator.data, 'elements', None) or {}
    element_entities = []
    for element in elements.values():
        element_entities.append(HertekElementStatusSensor(coordinator, entry, installation_id, installation_name, element))
    if element_entities:
        async_add_entities(element_entities)
def _zone_lookup(zones: list[dict], zone_id: int | None) -> dict | None:
    if zone_id is None:
        return None
    return next((z for z in zones if z.get("id") == zone_id), None)


def _has_category(alerts: list[dict], category: str) -> bool:
    c = category.upper()
    return any(upper(a.get("statusCategory")) == c for a in alerts)



class HertekElementStatusSensor(HertekEntityBase, SensorEntity):
    def __init__(self, coordinator, entry, installation_id: int, installation_name: str, element: dict) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self.element = element
        self.element_id = int(element.get("id"))
        self._attr_unique_id = f"{installation_id}_element_{self.element_id}_status"

        # Naam zo uniek mogelijk maken (zone + type + naam)
        zone_id = element.get("zoneId")
        zone_txt = ""
        z = _zone_lookup(self.coordinator.data.zones or [], zone_id)
        if z and z.get("number") is not None:
            zone_txt = f"Zone {z.get('number')}"
            if z.get("name"):
                zone_txt += f" {z.get('name')}"
        elif zone_id is not None:
            zone_txt = f"Zone {zone_id}"

        device_type = element.get("deviceType") or ""
        name = element.get("name") or f"Element {self.element_id}"

        parts = [p for p in [zone_txt, device_type, name] if p]
        self._attr_name = " ".join(parts) + " status"

    @property
    def native_value(self):
        alerts = self.coordinator.data.alerts or []
        # Alerts bevatten alleen afwijkingen; alles wat niet voorkomt is normaal
        for a in alerts:
            if int(a.get("id", -1)) == self.element_id:
                return a.get("statusCategory") or "UNKNOWN"
        return "NORMAL"

    @property
    def extra_state_attributes(self):
        # Handig voor diagnose en UI
        attrs = dict(self.element)
        alerts = self.coordinator.data.alerts or []
        match = next((a for a in alerts if int(a.get("id", -1)) == self.element_id), None)
        if match:
            attrs["alert"] = match
        return attrs

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


class HertekZoneStatusSensor(HertekEntityBase, SensorEntity):
    def __init__(
        self,
        coordinator,
        entry,
        installation_id: int,
        installation_name: str,
        zone_id: int,
    ) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self.zone_id = zone_id
        self._attr_unique_id = f"{installation_id}_zone_{zone_id}_status"

    @property
    def _zone(self) -> dict | None:
        return _zone_lookup(self.coordinator.data.zones or [], self.zone_id)

    @property
    def name(self):
        zone = self._zone or {}
        number = zone.get("number")
        label = f"Zone {number}" if number is not None else f"Zone {self.zone_id}"
        if zone.get("name"):
            label += f" {zone['name']}"
        return f"{label} status"

    @property
    def native_value(self):
        zone_alerts = [a for a in (self.coordinator.data.alerts or []) if a.get("zoneId") == self.zone_id]
        if not zone_alerts:
            return "Geen melding"
        if _has_category(zone_alerts, "FIRE"):
            return "Brandmelding"
        if _has_category(zone_alerts, "FAULT"):
            return "Storing"
        if _has_category(zone_alerts, "DISABLEMENT"):
            return "Uitgeschakeld"
        status = upper(zone_alerts[0].get("statusCategory")) or "UNKNOWN"
        return STATUSCATEGORY_NL.get(status, "Afwijking")

    @property
    def extra_state_attributes(self):
        zone = self._zone or {}
        zone_alerts = [a for a in (self.coordinator.data.alerts or []) if a.get("zoneId") == self.zone_id]
        return {
            "zone_id": self.zone_id,
            "zone_number": zone.get("number"),
            "zone_name": zone.get("name"),
            "active_alerts_count": len(zone_alerts),
            "active_alerts": zone_alerts,
        }


class HertekDeviceStatusSensor(HertekEntityBase, SensorEntity):
    def __init__(
        self,
        coordinator,
        entry,
        installation_id: int,
        installation_name: str,
        device: dict,
    ) -> None:
        super().__init__(coordinator, entry, installation_id, installation_name)
        self.device = device
        key = _device_unique_key(device, device.get("zoneId"))
        self._attr_unique_id = f"{installation_id}_device_{key}"

    @property
    def name(self):
        device_type = DEVICETYPE_NL.get(upper(self.device.get("deviceType")), self.device.get("deviceType") or "Sensor")
        name = self.device.get("name")
        if name:
            return f"{device_type} {name} status"

        loop = self.device.get("loop")
        address = self.device.get("address")
        suffix = []
        if loop is not None:
            suffix.append(f"Lus {loop}")
        if address is not None:
            suffix.append(f"Adres {address}")
        if suffix:
            return f"{device_type} {' '.join(suffix)} status"
        return f"{device_type} status"

    @property
    def native_value(self):
        match = self._active_alert
        if not match:
            return "Geen melding"

        category = upper(match.get("statusCategory")) or "UNKNOWN"
        if category == "FIRE":
            return "Brandmelding"
        if category == "FAULT":
            return "Storing"
        if category == "DISABLEMENT":
            return "Uitgeschakeld"
        return STATUSCATEGORY_NL.get(category, "Afwijking")

    @property
    def _active_alert(self) -> dict | None:
        alerts = self.coordinator.data.alerts or []

        candidates = [
            a
            for a in alerts
            if a.get("zoneId") == self.device.get("zoneId")
            and a.get("loop") == self.device.get("loop")
            and a.get("address") == self.device.get("address")
        ]
        if candidates:
            return candidates[0]

        name = self.device.get("name")
        if name:
            by_name = [
                a
                for a in alerts
                if a.get("zoneId") == self.device.get("zoneId")
                and a.get("name") == name
                and upper(a.get("deviceType")) == upper(self.device.get("deviceType"))
            ]
            if by_name:
                return by_name[0]

        return None

    @property
    def extra_state_attributes(self):
        return {
            "zone_id": self.device.get("zoneId"),
            "zone_number": self.device.get("zoneNumber"),
            "zone_name": self.device.get("zoneName"),
            "loop": self.device.get("loop"),
            "address": self.device.get("address"),
            "device_type": self.device.get("deviceType"),
            "device_name": self.device.get("name"),
            "active_alert": self._active_alert,
        }
