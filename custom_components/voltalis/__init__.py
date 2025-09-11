"""Voltalis integration."""
from datetime import datetime, timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VOLTALIS_CONTROLLER
from .controller import VoltalisController

PLATFORMS: list[Platform] = [Platform.CLIMATE,
                             Platform.WATER_HEATER, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    controller = hass.data[DOMAIN][entry.entry_id][VOLTALIS_CONTROLLER]

    async def handle_set_global_preset(call):
        preset = call.data["preset"]
        duration = call.data.get("duration")

        request_body = {
            "mode": preset,
            "enabled": True,
            "untilFurtherNotice": duration is None,
        }

        if duration is not None:
            end_time = datetime.now(datetime.timezone.utc) + \
                timedelta(hours=int(duration))
            request_body["endDate"] = end_time.isoformat() + "Z"

        # Appliquer à toutes les appliances (si c’est global)
        for appliance in controller.appliances:
            await appliance.api.async_set_manualsetting(
                json=request_body,
                programming_id=appliance.idManualSetting
            )

        await controller.coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, "set_global_preset", handle_set_global_preset
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up voltalis from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    controller = VoltalisController(hass)
    hass.data[DOMAIN][entry.entry_id] = {
        VOLTALIS_CONTROLLER: controller,
    }

    if not await controller.async_setup_entry(entry):
        return False

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
