import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration

from .api import HomeWizardCloudApi
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD, SERVICE_IMPORT_DAY
from .coordinator import HomeWizardCloudDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_IMPORT_DAY_SCHEMA = vol.Schema({vol.Required("date"): cv.date})

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    integration = await async_get_integration(hass, DOMAIN)

    api = HomeWizardCloudApi(
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        session,
        integration.version
    )

    coordinator = HomeWizardCloudDataUpdateCoordinator(
        hass,
        api,
        entry.data["home_id"]
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_import_day(call: ServiceCall) -> None:
        for entry_data in hass.data[DOMAIN].values():
            await entry_data["coordinator"].async_import_day(call.data["date"])

    if not hass.services.has_service(DOMAIN, SERVICE_IMPORT_DAY):
        hass.services.async_register(
            DOMAIN,
            SERVICE_IMPORT_DAY,
            _async_import_day,
            schema=SERVICE_IMPORT_DAY_SCHEMA,
        )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Unload all platforms (sensors, etc.)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up the memory
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok