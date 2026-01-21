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
    for value in coordinator.data:
        entities.append(HomeWizardCloudWaterSensor(coordinator, value["type"], value["title"]))

    async_add_entities(entities)

class HomeWizardCloudWaterSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, sensor_type, name):
        super().__init__(coordinator)

        self._type = sensor_type
        self._attr_name = f"HomeWizard {name}"
        self._attr_unique_id = f"{coordinator.home_id}_{sensor_type}"

        # Use TOTAL for daily values that reset at midnight
        self._attr_state_class = SensorStateClass.TOTAL
        
        # Assign Device Class based on type
        type_lower = sensor_type.lower()
        
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
            "name": f"HomeWizard Home {self.coordinator.home_id}",
            "manufacturer": "HomeWizard",
        }

    @property
    def native_value(self):
        """Return the state of the sensor as a float."""
        if not self.coordinator.data:
            return None

        for item in self.coordinator.data:
            if item["type"] == self._type:
                # Get the raw string value (e.g. "1.234" or "1 234,50")
                raw_value = str(item.get("displayValue", "0"))
                try:
                    # Remove spaces and normalize decimal separator
                    clean_value = raw_value.replace(" ", "").replace(",", ".")
                    return float(clean_value)
                except ValueError:
                    _LOGGER.warning("Could not convert value '%s' to float", raw_value)
                    return None
        return None

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement normalized for HA."""
        for item in self.coordinator.data:
            if item["type"] == self._type:
                unit = item.get("displayUnit")
                if unit == "m3":
                    return "m³"
                return unit
        return None
