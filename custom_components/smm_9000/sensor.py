"""Sensor platform for SMM-9000."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SMM9000DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def parse_sensor_value(value_str: str) -> tuple[float | None, str]:
    """Parse sensor value string and return value and unit."""
    if not value_str:
        return None, ""
    
    # Remove whitespace
    value_str = value_str.strip()
    
    # Parse temperature (e.g., "10.6C", "-2.5C")
    temp_match = re.match(r"([-+]?\d+\.?\d*)\s*C", value_str, re.IGNORECASE)
    if temp_match:
        try:
            return float(temp_match.group(1)), UnitOfTemperature.CELSIUS
        except ValueError:
            pass
    
    # Parse numeric value (e.g., "0", "100")
    num_match = re.match(r"([-+]?\d+\.?\d*)", value_str)
    if num_match:
        try:
            return float(num_match.group(1)), ""
        except ValueError:
            pass
    
    return None, ""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMM-9000 sensor entities."""
    coordinator: SMM9000DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Get list of sensors from coordinator data
    sensors = coordinator.data.get("sensors", {}) if coordinator.data else {}
    
    if not sensors:
        # If sensors are not loaded yet, request data
        await coordinator.async_request_refresh()
        sensors = coordinator.data.get("sensors", {}) if coordinator.data else {}
    
    entities = []
    
    # Create entities for each sensor
    for sensor_id, sensor_data in sensors.items():
        sensor_items = sensor_data.get("items", [])
        
        for idx, item in enumerate(sensor_items):
            name = item.get("name", "").strip().rstrip(":")
            value_str = item.get("value", "")
            sensor_type = item.get("type", "")
            
            if not name or not value_str:
                continue
            
            # Determine sensor type by name or image
            image = item.get("image", "")
            device_class = None
            unit = ""
            state_class = SensorStateClass.MEASUREMENT
            
            # Parse value to determine unit of measurement
            parsed_value, parsed_unit = parse_sensor_value(value_str)
            
            if "temperature" in image.lower() or "T" in name or parsed_unit == UnitOfTemperature.CELSIUS:
                device_class = SensorDeviceClass.TEMPERATURE
                unit = UnitOfTemperature.CELSIUS
            elif "precipitation" in image.lower() or "P" in name:
                # Precipitation sensor - unit not specified in value, use mm
                device_class = None
                unit = "mm"
            else:
                # Use unit from parsed value if available
                unit = parsed_unit
            
            entity = SMM9000Sensor(
                coordinator,
                f"{sensor_id}_{idx}",
                name,
                sensor_type,
                device_class,
                unit,
                state_class,
            )
            entities.append(entity)
    
    async_add_entities(entities)


class SMM9000Sensor(CoordinatorEntity[SMM9000DataUpdateCoordinator], SensorEntity):
    """Representation of a SMM-9000 sensor."""

    def __init__(
        self,
        coordinator: SMM9000DataUpdateCoordinator,
        sensor_key: str,
        sensor_name: str,
        sensor_type: str,
        device_class: SensorDeviceClass | None,
        unit: str,
        state_class: SensorStateClass,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        self._sensor_name = sensor_name
        self._sensor_type = sensor_type
        self._device_class = device_class
        self._unit = unit
        self._state_class = state_class
        
        self._attr_name = f"SMM-9000 {sensor_name}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sensor_{sensor_key}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        sensors = self.coordinator.data.get("sensors", {}) if self.coordinator.data else {}
        
        # Find sensor value by key
        for sensor_id, sensor_data in sensors.items():
            sensor_items = sensor_data.get("items", [])
            for idx, item in enumerate(sensor_items):
                if f"{sensor_id}_{idx}" == self._sensor_key:
                    value_str = item.get("value", "")
                    value, _ = parse_sensor_value(value_str)
                    return value
        
        return None
