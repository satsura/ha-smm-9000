"""The SMM-9000 integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SMM9000DataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.SENSOR]

type SMM9000ConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMM-9000 from a config entry."""
    coordinator = SMM9000DataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SMM9000DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.websocket_client.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
