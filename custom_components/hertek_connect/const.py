DOMAIN = "hertek_connect"

CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_INSTALLATION_ID = "installation_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_BASE_URL = "https://api.hertekconnect.nl"
DEFAULT_SCAN_INTERVAL_SECONDS = 30
MIN_SCAN_INTERVAL_SECONDS = 10
MAX_SCAN_INTERVAL_SECONDS = 3600

HTTP_TIMEOUT_SECONDS = 20

# API paths
PATH_REQUEST_TOKEN = "/api/v1/auth/request_token"
PATH_INSTALLATIONS = "/api/v1/installations"
PATH_ZONES = "/api/v1/installations/{installationId}/zones"
PATH_ALERTS = "/api/v1/installations/{installationId}/alerts"
PATH_ELEMENTS = "/api/v1/installations/{installationId}/zones/{zoneId}/elements"

# Service
SERVICE_REFRESH = "refresh"

# Presentation mappings
STATUSCATEGORY_NL = {
    "NORMAL": "Normaal",
    "FIRE": "Brandmelding",
    "FAULT": "Storing",
    "DISABLEMENT": "Uitgeschakeld",
    "TEST": "Test",
    "PREALARM": "Vooralarm",
    "UNKNOWN": "Onbekend",
}

CONNECTIONSTATUS_NL = {
    "OK": "Online",
    "OFFLINE": "Offline",
    "DISCONNECTED": "Verbinding verbroken",
    "CONNECTING": "Verbinden",
    "UNKNOWN": "Onbekend",
}

DEVICETYPE_NL = {
    "CALL POINT": "Handbrandmelder",
    "MANUAL CALL POINT": "Handbrandmelder",
    "SMOKE DETECTOR": "Rookmelder",
    "HEAT DETECTOR": "Warmtemelder",
    "MULTI SENSOR": "Multisensor",
    "CONTROL PANEL": "Brandmeldcentrale",
    "IO MODULE": "I/O-module",
    "INPUT MODULE": "Ingangsmodule",
    "OUTPUT MODULE": "Uitgangsmodule",
    "RELAY": "Relais",
    "SOUNDER": "Sirene",
    "SOUNDERS": "Sirene",
    "BEACON": "Flitslicht",
    "ASPIRATION": "Aspiratiesysteem",
    "GAS DETECTOR": "Gasdetector",
}
