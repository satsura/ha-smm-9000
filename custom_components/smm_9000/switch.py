"""Switch platform for SMM-9000 zones."""
from __future__ import annotations

import asyncio
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
            str(zone_id),
            zone_data.get("name", f"Zone {zone_id}").strip() or f"Zone {zone_id}"
        )
        for zone_id, zone_data in zones.items()
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
            _LOGGER.debug("Setting zone %s state to %s", self._zone_id, state)
            response = await self.coordinator.websocket_client.send_request(
                METHOD_HOME_DATA_SET, data, timeout=5, require_auth=True
            )
            _LOGGER.debug("Response from HOME_DATA_SET: %s", response)
            
            if response and response.get("success"):
                # Небольшая задержка, чтобы устройство успело обработать изменение
                await asyncio.sleep(0.5)
                # Запрашиваем обновление данных для получения актуального состояния
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
            else:
                # Извлекаем сообщение об ошибке
                error_msg = response.get("message", "") if response else ""
                errors = response.get("errors", {}) if response else {}
                
                # Формируем понятное сообщение об ошибке
                if errors:
                    error_parts = [f"{k}: {v}" for k, v in errors.items()]
                    error_msg = ", ".join(error_parts) if error_parts else "unknown error"
                elif error_msg:
                    error_msg = error_msg
                else:
                    error_msg = "unknown error"
                
                _LOGGER.error("Failed to set zone state: %s (response: %s)", error_msg, response)
                raise Exception(f"Failed to set zone state: {error_msg}")
        except Exception as e:
            _LOGGER.error("Error setting zone state: %s", e, exc_info=True)
            raise
