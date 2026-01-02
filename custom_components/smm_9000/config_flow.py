"""Config flow for SMM-9000 integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, METHOD_DEFAULTS_GET
from .websocket_client import SMM9000WebSocketClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.1.166"): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class CannotConnect(config_entries.ConfigFlowError):
    """Error to indicate we cannot connect."""


class InvalidAuth(config_entries.ConfigFlowError):
    """Error to indicate there is invalid auth."""


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    client = SMM9000WebSocketClient(data[CONF_HOST], data[CONF_PASSWORD])
    
    try:
        await client.connect()
        # Ждем немного для установления соединения
        await asyncio.sleep(1)
        
        if not client.connected:
            await client.disconnect()
            raise CannotConnect
        
        # Попробуем получить настройки для проверки подключения
        response = await client.send_request(METHOD_DEFAULTS_GET, {}, timeout=5, require_auth=False)
        
        if not response or not response.get("success"):
            await client.disconnect()
            raise InvalidAuth
        
        await client.disconnect()
        return {"title": f"SMM-9000 ({data[CONF_HOST]})"}
    except (CannotConnect, InvalidAuth):
        raise
    except Exception as e:
        try:
            await client.disconnect()
        except Exception:
            pass
        _LOGGER.exception("Unexpected error validating input")
        raise CannotConnect from e


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMM-9000."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
