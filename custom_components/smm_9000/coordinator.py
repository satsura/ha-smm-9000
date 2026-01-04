"""Data update coordinator for SMM-9000."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_RECONNECT_INTERVAL, METHOD_HOME_DATA_GET
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
            update_interval=None,  # Real-time updates via WebSocket
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
        
        # Update data based on message
        current_data = self.data or {}
        
        # Process different message types
        if "method" in message:
            method = message.get("method")
            if method == "HOME_DATA_GET" and message.get("success"):
                # Update device data
                home_data = message.get("data", {})
                # Extract zones from the list
                zones_list = home_data.get("list", [])
                zones = {}
                sensors = {}
                for item in zones_list:
                    if item.get("type") == "zone":
                        zone_id = item.get("id")
                        if zone_id:
                            zones[int(zone_id)] = {
                                "id": zone_id,
                                "name": item.get("name", ""),
                                "enabled": item.get("enabled", False),
                            }
                    elif item.get("type") == "sensor":
                        sensor_id = item.get("id")
                        if sensor_id:
                            # Combine line_one and line_two into a single items list
                            items = []
                            # Add items from line_one
                            for line_item in item.get("line_one", []):
                                items.append({
                                    **line_item,
                                    "type": "temperature" if "temperature" in line_item.get("image", "").lower() else "precipitation" if "precipitation" in line_item.get("image", "").lower() else "unknown"
                                })
                            # Add items from line_two
                            for line_item in item.get("line_two", []):
                                items.append({
                                    **line_item,
                                    "type": "temperature" if "temperature" in line_item.get("image", "").lower() else "precipitation" if "precipitation" in line_item.get("image", "").lower() else "unknown"
                                })
                            sensors[int(sensor_id)] = {
                                "id": sensor_id,
                                "items": items,
                            }
                current_data["zones"] = zones
                current_data["sensors"] = sensors
                current_data["home_data"] = home_data
                self.async_set_updated_data(current_data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from SMM-9000."""
        if not self.websocket_client.connected:
            await self._ensure_connected()
        
        # Request current data
        try:
            response = await self.websocket_client.send_request(METHOD_HOME_DATA_GET, {}, timeout=5)
            if response and response.get("success"):
                home_data = response.get("data", {})
                # Extract zones and sensors from the list
                zones_list = home_data.get("list", [])
                zones = {}
                sensors = {}
                for item in zones_list:
                    if item.get("type") == "zone":
                        zone_id = item.get("id")
                        if zone_id:
                            zones[int(zone_id)] = {
                                "id": zone_id,
                                "name": item.get("name", ""),
                                "enabled": item.get("enabled", False),
                            }
                    elif item.get("type") == "sensor":
                        sensor_id = item.get("id")
                        if sensor_id:
                            # Combine line_one and line_two into a single items list
                            items = []
                            # Add items from line_one
                            for line_item in item.get("line_one", []):
                                items.append({
                                    **line_item,
                                    "type": "temperature" if "temperature" in line_item.get("image", "").lower() else "precipitation" if "precipitation" in line_item.get("image", "").lower() else "unknown"
                                })
                            # Add items from line_two
                            for line_item in item.get("line_two", []):
                                items.append({
                                    **line_item,
                                    "type": "temperature" if "temperature" in line_item.get("image", "").lower() else "precipitation" if "precipitation" in line_item.get("image", "").lower() else "unknown"
                                })
                            sensors[int(sensor_id)] = {
                                "id": sensor_id,
                                "items": items,
                            }
                return {"zones": zones, "sensors": sensors, "home_data": home_data}
            raise UpdateFailed("Failed to fetch data")
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def _ensure_connected(self) -> None:
        """Ensure WebSocket connection is established."""
        if not self.websocket_client.connected:
            try:
                await self.websocket_client.connect()
                # Give time for connection and authorization
                await asyncio.sleep(2)
            except Exception as e:
                _LOGGER.error("Failed to connect: %s", e)
                raise UpdateFailed(f"Connection failed: {e}") from e

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and start WebSocket connection."""
        # Try to connect, but don't block startup if device is unavailable
        try:
            await self._ensure_connected()
        except UpdateFailed:
            _LOGGER.warning("Device not available during startup, will retry in background")
        await super().async_config_entry_first_refresh()
        
        # Start background task to maintain connection (does not block startup)
        if not self._reconnect_task or self._reconnect_task.done():
            self._reconnect_task = self.hass.async_create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Loop to maintain WebSocket connection."""
        while True:
            try:
                await asyncio.sleep(DEFAULT_RECONNECT_INTERVAL)
                if not self.websocket_client.connected:
                    _LOGGER.info("Reconnecting to SMM-9000...")
                    try:
                        await self._ensure_connected()
                    except UpdateFailed:
                        _LOGGER.debug("Reconnection attempt failed, will retry later")
                        continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error("Error in reconnect loop: %s", e)
