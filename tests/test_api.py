"""Tests for the HomeWizard Cloud API client."""
import time
from datetime import datetime

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.homewizard_cloud_watermeter.api import HomeWizardCloudApi

TOKEN_URL = "https://api.homewizardeasyonline.com/v1/auth/account/token"


def make_api(hass):
    return HomeWizardCloudApi("user@example.com", "secret", async_get_clientsession(hass), "0.0.0")


async def test_authenticate_success(hass, aioclient_mock):
    aioclient_mock.get(TOKEN_URL, json={"access_token": "tok", "expires_in": 3600})
    api = make_api(hass)

    assert await api.async_authenticate() is True
    assert api._token == "tok"


async def test_authenticate_failure(hass, aioclient_mock):
    aioclient_mock.get(TOKEN_URL, status=401)
    api = make_api(hass)

    assert await api.async_authenticate() is False
    assert api._token is None


async def test_valid_token_is_reused(hass, aioclient_mock):
    api = make_api(hass)
    api._token = "cached"
    api._token_expires_at = time.time() + 1000

    assert await api.async_ensure_token() == "cached"
    assert aioclient_mock.call_count == 0


async def test_expired_token_is_renewed(hass, aioclient_mock):
    aioclient_mock.get(TOKEN_URL, json={"access_token": "fresh", "expires_in": 3600})
    api = make_api(hass)
    api._token = "stale"
    api._token_expires_at = time.time() - 1

    assert await api.async_ensure_token() == "fresh"


async def test_get_tsdb_data(hass, aioclient_mock):
    aioclient_mock.get(TOKEN_URL, json={"access_token": "tok", "expires_in": 3600})
    aioclient_mock.post(
        "https://tsdb-reader.homewizard.com/devices/date/2026/07/15",
        json={"values": [{"time": "2026-07-15T23:00:00+00:00", "water": 5.0}]},
    )
    api = make_api(hass)

    data = await api.async_get_tsdb_data(datetime(2026, 7, 15), "Europe/Paris", "water/ABC")

    assert data["values"][0]["water"] == 5.0
    payload = aioclient_mock.mock_calls[-1][2]
    assert payload["devices"][0]["identifier"] == "water/ABC"
    assert payload["tz"] == "Europe/Paris"
