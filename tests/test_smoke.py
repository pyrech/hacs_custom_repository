"""Smoke test against the real HomeWizard cloud API.

Verifies the API contract the integration relies on still holds (auth,
locations, device list, TSDB shape). Only runs when HW_EMAIL/HW_PASSWORD
are set in the environment — i.e. the scheduled CI job — and is skipped
everywhere else, so the regular test suite stays offline.
"""
import os
from datetime import datetime, timedelta

import aiohttp
import pytest

from custom_components.homewizard_cloud_watermeter.api import HomeWizardCloudApi

pytestmark = pytest.mark.skipif(
    not (os.environ.get("HW_EMAIL") and os.environ.get("HW_PASSWORD")),
    reason="HW_EMAIL/HW_PASSWORD not set",
)


async def test_real_api_contract(socket_enabled):
    async with aiohttp.ClientSession() as session:
        api = HomeWizardCloudApi(
            os.environ["HW_EMAIL"], os.environ["HW_PASSWORD"], session, "smoke-test"
        )

        assert await api.async_authenticate() is True, "authentication failed"

        locations = await api.async_get_locations()
        assert locations, "no locations returned"
        assert "id" in locations[0], "location shape changed: missing 'id'"

        devices_data = await api.async_get_devices(locations[0]["id"])
        assert devices_data and "errors" not in devices_data, "device query failed"
        devices = devices_data["data"]["home"]["devices"]
        watermeters = [d for d in devices if d.get("type") == "watermeter"]
        assert watermeters, "no watermeter device found on the account"

        device = watermeters[0]
        assert "identifier" in device
        assert "onlineState" in device

        yesterday = datetime.now() - timedelta(days=1)
        stats = await api.async_get_tsdb_data(
            yesterday, "Europe/Paris", device["identifier"]
        )
        assert stats is not None, "TSDB query failed"
        assert "values" in stats, "TSDB shape changed: missing 'values'"
        assert stats["values"], "TSDB returned no values for yesterday"

        entry = stats["values"][0]
        assert "time" in entry, "TSDB entry shape changed: missing 'time'"
        assert "water" in entry, "TSDB entry shape changed: missing 'water'"
        # 'time' must stay parseable by the coordinator
        datetime.fromisoformat(entry["time"])
