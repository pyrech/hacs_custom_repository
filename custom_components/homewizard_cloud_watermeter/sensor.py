import logging
from homeassistant.components.sensor import (
    EntityCategory,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]

    if not coordinator.data:
        _LOGGER.error("No devices found, sensors will not be created")

    entities = []

    # Create a sensor for each homewizard device
    for value in coordinator.data.values():
        entities.append(HomeWizardDailyTotalSensor(coordinator, value))
        entities.append(HomeWizardWifiSensor(coordinator, value))
        entities.append(HomeWizardOnlineSensor(coordinator, value))

    async_add_entities(entities)

class HomeWizardBaseSensor(CoordinatorEntity):
    """Common base for all HomeWizard sensors."""
    _attr_has_entity_name = True

    def __init__(self, coordinator, value):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sanitized_identifier = value["device"].get("sanitized_identifier")

        # Unique ID needs to be unique per entity, so we append the class name or a suffix
        # This will be overridden or extended in child classes
        self._attr_unique_id = f"{self._sanitized_identifier}_{self.__class__.__name__}"

    @property
    def device_info(self):
        """Return device information to group all entities under the same device."""
        device = self.coordinator.data.get(self._sanitized_identifier)["device"]

        # Ensure we have a valid device
        if not device:
            return None

        return {
            "identifiers": {(DOMAIN, self._sanitized_identifier)},
            "name": device.get("name", "HomeWizard Watermeter"),
            "manufacturer": "HomeWizard",
            "model": device.get("model"),
            "hw_version": device.get("hardwareVersion"),
        }

class HomeWizardDailyTotalSensor(HomeWizardBaseSensor, SensorEntity):
    def __init__(self, coordinator, data):
        super().__init__(coordinator, data)

        self._attr_name = "Daily usage"
        self._attr_unique_id = f"{self._sanitized_identifier}_daily_total"
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_native_unit_of_measurement = data["unit"]

        # Use TOTAL for daily values that reset at midnight
        self._attr_state_class = SensorStateClass.TOTAL

    @property
    def native_value(self):
        """Return the state of the sensor as a float."""
        daily_total = self.coordinator.data.get(self._sanitized_identifier)["daily_total"]

        if not daily_total:
            return None

        try:
            return float(daily_total)
        except ValueError:
            _LOGGER.warning("Could not convert value '%s' to float", daily_total)
            return None

    @property
    def extra_state_attributes(self):
        """Return entity specific state attributes."""
        return {
            "statistic_id": f"{DOMAIN}:{self._sanitized_identifier}_total"
        }

class HomeWizardWifiSensor(HomeWizardBaseSensor, SensorEntity):
    def __init__(self, coordinator, data):
        super().__init__(coordinator, data)

        self._attr_name = "Wifi Signal"
        self._attr_unique_id = f"{self._sanitized_identifier}_wifi_signal"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = "mdi:wifi"
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        return self.coordinator.data.get(self._sanitized_identifier)["device"].get("wifiStrength", 0)

class HomeWizardOnlineSensor(HomeWizardBaseSensor, SensorEntity):
    def __init__(self, coordinator, data):
        super().__init__(coordinator, data)

        self._attr_name = "Online State"
        self._attr_unique_id = f"{self._sanitized_identifier}_online_state"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        return self.coordinator.data.get(self._sanitized_identifier)["device"].get("onlineState", "Unknown")
