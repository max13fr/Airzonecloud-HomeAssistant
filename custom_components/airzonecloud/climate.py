import logging
from typing import Any, Dict, List, Optional
from datetime import timedelta
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.util.temperature import convert as convert_temperature
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    SUPPORT_TARGET_TEMPERATURE,
)
from .const import CONF_USERNAME, CONF_PASSWORD

# init logger
_LOGGER = logging.getLogger(__name__)

# default refresh interval
SCAN_INTERVAL = timedelta(seconds=10)

AIRZONECLOUD_HVAC_MODES = [
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Airzonecloud platform"""
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    if username is None or password is None:
        _LOGGER.error("missing username or password config")
        return

    from AirzoneCloud import AirzoneCloud

    api = None
    try:
        api = AirzoneCloud(username, password)
    except Exception as err:
        _LOGGER.error(err)
        hass.services.call(
            "persistent_notification",
            "create",
            {"title": "Airzonecloud error", "message": str(err)},
        )
        return

    entities = []
    for installation in api.installations:
        for group in installation.groups:
            entities.append(AirzonecloudGroup(group))
            for device in group.devices:
                entities.append(AirzonecloudDevice(device))

    add_entities(entities)


class AirzonecloudDevice(ClimateEntity):
    """Representation of an Airzonecloud Device (a thermostat zone)"""

    def __init__(self, device):
        """Initialize the device"""
        self._device = device
        _LOGGER.info("init device {} ({})".format(self.name, self.unique_id))

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return "device_" + self._device.id

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} - {}".format(self._device.group.name, self._device.name)

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        mode = self._device.mode

        if self._device.is_on:
            if mode in [
                "cooling",
                "air-cooling",
                "radiant-cooling",
                "combined-cooling",
            ]:
                return HVAC_MODE_COOL

            if mode in [
                "heating",
                "air-heating",
                "radiant-heating",
                "combined-heating",
                "emergency-heating",
            ]:
                return HVAC_MODE_HEAT

            if mode == "ventilation":
                return HVAC_MODE_FAN_ONLY

            if mode == "dehumidify":
                return HVAC_MODE_DRY

        return HVAC_MODE_OFF

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return AIRZONECLOUD_HVAC_MODES

    @property
    def current_humidity(self) -> Optional[float]:
        """Return the current humidity."""
        return self._device.current_humidity

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._device.current_temperature

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        return self._device.target_temperature

    @property
    def target_temperature_step(self) -> Optional[float]:
        """Return the supported step of target temperature."""
        return self._device.step_temperature

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return convert_temperature(
            self._device.min_temperature, TEMP_CELSIUS, self.temperature_unit
        )

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return convert_temperature(
            self._device.max_temperature, TEMP_CELSIUS, self.temperature_unit
        )

    def set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._device.set_temperature(round(float(temperature), 1))

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_OFF:
            self._device.turn_off()
        else:
            if not self._device.is_on:
                self._device.turn_on(auto_refresh=False)

            # set hvac mode on parent system
            if hvac_mode == HVAC_MODE_HEAT:
                self._device.group.set_mode("heating")
            elif hvac_mode == HVAC_MODE_COOL:
                self._device.group.set_mode("cooling")
            elif hvac_mode == HVAC_MODE_DRY:
                self._device.group.set_mode("dehumidify")
            elif hvac_mode == HVAC_MODE_FAN_ONLY:
                self._device.group.set_mode("ventilation")

    def turn_on(self):
        """Turn on."""
        self._device.turn_on()

    def turn_off(self):
        """Turn off."""
        self._device.turn_off()


class AirzonecloudGroup(ClimateEntity):
    """Representation of an Airzonecloud Group (the air conditioner hardware)"""

    def __init__(self, group):
        """Initialize the group"""
        self._group = group
        _LOGGER.info("init group {} ({})".format(self.name, self.unique_id))

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return "group_" + self._group.id

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{}".format(self._group.name)

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        mode = self._group.mode

        if self._group.is_on:
            if mode in [
                "cooling",
                "air-cooling",
                "radiant-cooling",
                "combined-cooling",
            ]:
                return HVAC_MODE_COOL

            if mode in [
                "heating",
                "air-heating",
                "radiant-heating",
                "combined-heating",
                "emergency-heating",
            ]:
                return HVAC_MODE_HEAT

            if mode == "ventilation":
                return HVAC_MODE_FAN_ONLY

            if mode == "dehumidify":
                return HVAC_MODE_DRY

        return HVAC_MODE_OFF

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return AIRZONECLOUD_HVAC_MODES

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return 0

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_OFF:
            self._group.set_mode("stop")
        elif hvac_mode == HVAC_MODE_HEAT:
            self._group.set_mode("heating")
        elif hvac_mode == HVAC_MODE_COOL:
            self._group.set_mode("cooling")
        elif hvac_mode == HVAC_MODE_DRY:
            self._group.set_mode("dehumidify")
        elif hvac_mode == HVAC_MODE_FAN_ONLY:
            self._group.set_mode("ventilation")

    def turn_on(self):
        """Turn on."""
        self._group.turn_on()

    def turn_off(self):
        """Turn off."""
        self._group.turn_off()

    def update(self):
        self._group.refresh_devices()
