import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration

from .api import HomeWizardCloudApi
from .const import DOMAIN, CONF_EMAIL, CONF_PASSWORD
from .coordinator import HomeWizardCloudDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

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

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Unload all platforms (sensors, etc.)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up the memory
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok