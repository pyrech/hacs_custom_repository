import aiohttp
import async_timeout
import logging
import time

_LOGGER = logging.getLogger(__name__)

class HomeWizardCloudApi:
    """ApiClient for HomeWizard Cloud API."""

    def __init__(self, username, password, session: aiohttp.ClientSession, version: str):
        self._username = username
        self._password = password
        self._session = session
        self._token = None
        self._token_expires_at = 0
        self._user_agent = f"HomeWizardCloudWatermeter/{version} (+https://github.com/pyrech/homewizard_cloud_watermeter)"

    async def async_authenticate(self) -> bool:
        """Authenticate with the Basic Auth to get a Bearer token."""
        url = "https://api.homewizardeasyonline.com/v1/auth/account/token"
        auth = aiohttp.BasicAuth(self._username, self._password)

        try:
            async with async_timeout.timeout(10):
                async with self._session.get(url, auth=auth, headers={"User-Agent": self._user_agent}) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._token = data.get("access_token")
                        # Store expiration time (current time + expires_in)
                        # We subtract 60 seconds as a safety margin
                        expires_in = data.get("expires_in", 3600)
                        self._token_expires_at = time.time() + expires_in - 60
                        _LOGGER.debug("Successfully authenticated. Token expires in %s s", expires_in)
                        return True
                    
                    _LOGGER.error("Authentication failed with status: %s", response.status)
                    return False
        except Exception as ex:
            _LOGGER.error("Error connecting to HomeWizard API: %s", ex)
            return False

    async def async_get_locations(self) -> list:
            """Get the list of locations associated with the account."""
            url = "https://homes.api.homewizard.com/locations"
            headers = await self.get_headers()

            try:
                async with async_timeout.timeout(10):
                    async with self._session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        _LOGGER.error("Failed to fetch locations: %s", response.status)
                        return []
            except Exception as ex:
                _LOGGER.error("Error fetching locations: %s", ex)
                return []

    async def async_get_energy_panel_values(self, home_id: int, period: str):
        """Fetch energy panel values for a specific period."""
        url = "https://api.homewizard.energy/v1/graphql"
        headers = await self.get_headers()
        
        payload = {
            "operationName": "EnergyPanelValues",
            "variables": {
                "homeId": home_id,
                "period": period
            },
            "query": (
                "query EnergyPanelValues($homeId: Int!, $period: TsdbPeriod!) { "
                "home(id: $homeId) { "
                "energyPanel { "
                "values(period: $period) { "
                "type title displayValue displayUnit "
                "additionalValue { type title displayString displayValue displayUnit } "
                "} } } }"
            )
        }

        try:
            async with async_timeout.timeout(10):
                async with self._session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    _LOGGER.error("GraphQL energy panel request failed: %s", response.status)
                    return None
        except Exception as ex:
            _LOGGER.error("Error during energy panel GraphQL request: %s", ex)
            return None

    async def get_headers(self) -> dict:
        """Get headers for GraphQL/API requests."""
        token = await self.async_ensure_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": self._user_agent,
        }

    async def async_ensure_token(self) -> str:
        """Check if token is valid and renew it if necessary."""
        if not self._token or time.time() > self._token_expires_at:
            _LOGGER.debug("Token expired or missing, renewing...")
            await self.async_authenticate()
        return self._token
