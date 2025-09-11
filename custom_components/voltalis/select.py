import logging
from homeassistant.components.select import SelectEntity

from custom_components.voltalis.aiovoltalis import ProgramType
from custom_components.voltalis.entity import CoordinatorEntity, DeviceInfo
from .const import DOMAIN, VOLTALIS_CONTROLLER, VOLTALIS_PRESET_MODES


async def async_setup_entry(hass, entry, async_add_entities):
    controller = hass.data[DOMAIN][entry.entry_id][VOLTALIS_CONTROLLER]
    async_add_entities([VoltalisPresetSelect(
        controller.coordinator, controller)])

_LOGGER = logging.getLogger(__name__)


class VoltalisPresetSelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, controller):
        super().__init__(coordinator)
        self.controller = controller
        self._attr_name = "Voltalis Mode Global"
        # Liste des noms de tous les programs disponibles + preset "aucun préreglage"
        self._none_option = "aucun préreglage"
        self._attr_unique_id = "global_mode"
        self._attr_options = [
            program.name for program in controller.programs] + [self._none_option]
        self._programs_by_name = {
            program.name: program for program in controller.programs}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "global_mode")},
            name="Voltalis Global Mode",
            manufacturer="Voltalis",
            model="Preset Select",
        )
        # Définir l'option courante dynamiquement
        self._attr_current_option = None

    @property
    def current_option(self):
        # Priorité : DEFAULT puis USER
        enabled_program = next(
            (p for p in self.controller.programs if p.isEnabled and getattr(
                p, '_program_type', None) == ProgramType.DEFAULT),
            None
        )
        if not enabled_program:
            enabled_program = next(
                (p for p in self.controller.programs if p.isEnabled and getattr(
                    p, '_program_type', None) == ProgramType.USER),
                None
            )
        if enabled_program:
            return enabled_program.name
        return self._none_option

    async def async_select_option(self, option: str):
        # Si "aucun préreglage" sélectionné, désactive le program actuellement activé
        if option == self._none_option:
            _LOGGER.debug("Désactivation de tous les programmes")
            enabled_program = next(
                (p for p in self.controller.programs if p.isEnabled), None)
            if enabled_program:
                curjson = {
                    "enabled": False,
                    "name": enabled_program.name,
                }
                if hasattr(enabled_program, "_program_type") and getattr(enabled_program, "_program_type", None) and hasattr(enabled_program, "api"):
                    if getattr(enabled_program, "_program_type").name == "USER":
                        await enabled_program.api.async_set_user_program_state(
                            json=curjson,
                            program_id=enabled_program.id
                        )
                    else:
                        await enabled_program.api.async_set_default_program_state(
                            json=curjson,
                            program_id=enabled_program.id
                        )
        else:
            # Active uniquement le program sélectionné (le backend désactive les autres)
            _LOGGER.debug("Activation du programme %s", option)
            program = self._programs_by_name.get(option)
            _LOGGER.debug("Programme trouvé: %s", program)
            if program:
                curjson = program.get_json().copy()
                curjson["enabled"] = True

                if program._program_type == ProgramType.USER:
                    await program.api.async_set_user_program_state(
                        json=curjson,
                        program_id=program.id
                    )
                else:
                    curjson["untilFurtherNotice"] = True
                    curjson["modeEndDate"] = None
                    _LOGGER.debug(curjson)
                    await program.api.async_set_default_program_state(
                        json=curjson,
                        program_id=program.id
                    )
        await self.coordinator.async_request_refresh()
