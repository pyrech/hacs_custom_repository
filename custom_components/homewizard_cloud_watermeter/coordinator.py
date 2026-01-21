from datetime import timedelta, datetime
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HomeWizardCloudDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, home_id):
        """Initialize the coordinator."""
        self.api = api
        self.home_id = home_id
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=60),
        )

    async def _async_update_data(self):
        # Get the current time in the user's configured timezone
        now = dt_util.now()
        current_period = now.strftime("%Y/%m/%d")

        _LOGGER.debug("Fetching data for period: %s", current_period)
        
        try:
            data = await self.api.async_get_energy_panel_values(self.home_id, current_period)
            if not data or "errors" in data:
                raise UpdateFailed(f"Error fetching GraphQL data: {data.get('errors')}")
            
            # Return the list of values directly
            return data["data"]["home"]["energyPanel"]["values"]
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
