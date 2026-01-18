import logging
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    
    if not coordinator.data:
        _LOGGER.error("No data found in coordinator, sensors will not be created")
        return

    entities = []
    # Create a sensor for each value returned by the energyPanel
    for value in coordinator.data.values():
        entities.append(HomeWizardCloudWaterSensor(coordinator, value))

    async_add_entities(entities)

class HomeWizardCloudWaterSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, value):
        super().__init__(coordinator)

        self._type = value["type"]
        self._attr_name = f"HomeWizard {value['title']}"
        self._attr_unique_id = f"{coordinator.home_id}_{self._type}"

        # Use TOTAL for daily values that reset at midnight
        self._attr_state_class = SensorStateClass.TOTAL
        
        # Assign Device Class based on type
        type_lower = self._type.lower()
        
        if "water" in type_lower:
            self._attr_device_class = SensorDeviceClass.WATER
        # elif "gas" in type_lower:
        #     self._attr_device_class = SensorDeviceClass.GAS
        # elif "energy" in type_lower:
        #     self._attr_device_class = SensorDeviceClass.ENERGY

    @property
    def device_info(self):
        """Return device information about this entity."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.home_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": "HomeWizard",
        }

    @property
    def native_value(self):
        """Return the state of the sensor as a float."""
        if not self.coordinator.data or self._type not in self.coordinator.data:
            return None

        item = self.coordinator.data[self._type]
        # Get the raw string value (e.g. "1.234" or "1 234,50")
        raw_value = str(item.get("displayValue", "0"))
        try:
            # Remove spaces and normalize decimal separator
            clean_value = raw_value.replace(" ", "").replace(",", ".")
            return float(clean_value)
        except ValueError:
            _LOGGER.warning("Could not convert value '%s' to float", raw_value)
            return None

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement normalized for HA."""
        if not self.coordinator.data or self._type not in self.coordinator.data:
            return None

        item = self.coordinator.data[self._type]
        unit = item.get("displayUnit")
        if unit == "m3":
            return "m³"
        return unit