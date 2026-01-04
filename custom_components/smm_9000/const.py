"""Constants for SMM-9000 integration."""
from typing import Final

DOMAIN: Final = "smm_9000"

DEFAULT_TIMEOUT = 10
DEFAULT_RECONNECT_INTERVAL = 30

# WebSocket methods
METHOD_LOGIN = "LOGIN_USER"
METHOD_DEFAULTS_GET = "DEFAULTS_GET"
METHOD_HOME_DATA_GET = "HOME_DATA_GET"
METHOD_HOME_DATA_SET = "HOME_DATA_SET"
METHOD_ZONES_DATA_SET = "ZONES_DATA_SET"  # Alternative method

# Configuration keys
CONF_HOST = "host"
CONF_PASSWORD = "password"
