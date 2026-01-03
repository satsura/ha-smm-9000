"""Switch platform for SMM-9000 zones."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, METHOD_HOME_DATA_SET
from .coordinator import SMM9000DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMM-9000 switch entities."""
    coordinator: SMM9000DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Получаем список зон из данных устройства
    zones = coordinator.data.get("zones", {}) if coordinator.data else {}
    
    # Создаем entities для каждой зоны
    entities = [
        SMM9000ZoneSwitch(
            coordinator,
            str(zone_data["id"]),
            zone_data.get("name", f"Zone {zone_data['id']}").strip() or f"Zone {zone_data['id']}"
        )
        for zone_data in zones.values()
    ]

    async_add_entities(entities)


class SMM9000ZoneSwitch(CoordinatorEntity[SMM9000DataUpdateCoordinator], SwitchEntity):
    """Representation of a SMM-9000 zone switch."""

    def __init__(
        self,
        coordinator: SMM9000DataUpdateCoordinator,
        zone_id: str,
        zone_name: str,
    ) -> None:
        """Initialize the zone switch."""
        super().__init__(coordinator)
        self._zone_id = int(zone_id)  # ID зоны как число
        self._zone_name = zone_name.strip() if zone_name.strip() else f"Зона {zone_id}"
        self._attr_name = f"SMM-9000 {self._zone_name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_zone_{zone_id}"

    @property
    def is_on(self) -> bool:
        """Return True if the zone is on."""
        # Получаем состояние зоны из данных координатора
        zones = self.coordinator.data.get("zones", {}) if self.coordinator.data else {}
        zone_data = zones.get(self._zone_id, {})
        
        # Состояние хранится в поле "enabled"
        return bool(zone_data.get("enabled", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the zone on."""
        await self._set_zone_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the zone off."""
        await self._set_zone_state(False)

    async def _set_zone_state(self, state: bool) -> None:
        """Set zone state via WebSocket."""
        data = {
            "id": int(self._zone_id),
            "enabled": state,
        }

        try:
            response = await self.coordinator.websocket_client.send_request(
                METHOD_HOME_DATA_SET, data, timeout=5, require_auth=True
            )
            if response and response.get("success"):
                # Запрашиваем обновление данных для получения актуального состояния
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
            else:
                error_msg = response.get("message", "unknown error") if response else "no response"
                _LOGGER.error("Failed to set zone state: %s", error_msg)
                raise Exception(f"Failed to set zone state: {error_msg}")
        except Exception as e:
            _LOGGER.error("Error setting zone state: %s", e)
            raise
