"""Data update coordinator for SMM-9000."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_RECONNECT_INTERVAL, METHOD_HOME_DATA_GET, METHOD_HOME_DATA_GET
from .websocket_client import SMM9000WebSocketClient

_LOGGER = logging.getLogger(__name__)


class SMM9000DataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from SMM-9000."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name="SMM-9000",
            update_interval=None,  # Обновление через WebSocket в реальном времени
        )
        self.config_entry = entry
        self.host = entry.data[CONF_HOST]
        self.password = entry.data[CONF_PASSWORD]
        self.websocket_client = SMM9000WebSocketClient(
            self.host, self.password, self._handle_websocket_message
        )
        self._reconnect_task: asyncio.Task | None = None

    def _handle_websocket_message(self, message: dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        _LOGGER.debug("Received WebSocket message: %s", message)
        
        # Обновляем данные на основе сообщения
        current_data = self.data or {}
        
        # Обрабатываем различные типы сообщений
        if "method" in message:
            method = message.get("method")
            if method == "HOME_DATA_GET" and message.get("success"):
                # Обновляем данные устройства
                home_data = message.get("data", {})
                # Извлекаем зоны из списка
                zones_list = home_data.get("list", [])
                zones = {}
                for item in zones_list:
                    if item.get("type") == "zone":
                        zone_id = item.get("id")
                        if zone_id:
                            zones[str(zone_id)] = {
                                "id": zone_id,
                                "name": item.get("name", ""),
                                "enabled": item.get("enabled", False),
                            }
                current_data["zones"] = zones
                current_data["home_data"] = home_data
                self.async_set_updated_data(current_data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from SMM-9000."""
        if not self.websocket_client.connected:
            await self._ensure_connected()
        
        # Запрашиваем текущие данные
        try:
            response = await self.websocket_client.send_request(METHOD_HOME_DATA_GET, {}, timeout=5)
            if response and response.get("success"):
                home_data = response.get("data", {})
                # Извлекаем зоны из списка
                zones_list = home_data.get("list", [])
                zones = {}
                for item in zones_list:
                    if item.get("type") == "zone":
                        zone_id = item.get("id")
                        if zone_id:
                            zones[str(zone_id)] = {
                                "id": zone_id,
                                "name": item.get("name", ""),
                                "enabled": item.get("enabled", False),
                            }
                return {"zones": zones, "home_data": home_data}
            raise UpdateFailed("Failed to fetch data")
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def _ensure_connected(self) -> None:
        """Ensure WebSocket connection is established."""
        if not self.websocket_client.connected:
            try:
                await self.websocket_client.connect()
                # Даем время на установление соединения и авторизацию
                await asyncio.sleep(2)
            except Exception as e:
                _LOGGER.error("Failed to connect: %s", e)
                raise UpdateFailed(f"Connection failed: {e}") from e

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and start WebSocket connection."""
        await self._ensure_connected()
        await super().async_config_entry_first_refresh()
        
        # Запускаем задачу для поддержания соединения
        if not self._reconnect_task or self._reconnect_task.done():
            self._reconnect_task = self.hass.async_create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Loop to maintain WebSocket connection."""
        while True:
            try:
                await asyncio.sleep(DEFAULT_RECONNECT_INTERVAL)
                if not self.websocket_client.connected:
                    _LOGGER.info("Reconnecting to SMM-9000...")
                    await self._ensure_connected()
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Error in reconnect loop: %s", e)
