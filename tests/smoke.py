"""Smoke test against the real HomeWizard cloud API.

Standalone script, deliberately outside pytest: the HA test plugin
restricts sockets to localhost, and the API client only needs aiohttp
anyway. Run by the scheduled smoke workflow with HW_EMAIL/HW_PASSWORD
set; verifies the API contract the integration relies on still holds
(auth, locations, device list, TSDB shape).
"""
import asyncio
import importlib.util
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp

# Load api.py directly: importing the package would pull homeassistant
# through custom_components/homewizard_cloud_watermeter/__init__.py.
_api_path = (
    Path(__file__).resolve().parent.parent
    / "custom_components" / "homewizard_cloud_watermeter" / "api.py"
)
_spec = importlib.util.spec_from_file_location("hw_api", _api_path)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
HomeWizardCloudApi = _module.HomeWizardCloudApi


async def main():
    async with aiohttp.ClientSession() as session:
        api = HomeWizardCloudApi(
            os.environ["HW_EMAIL"], os.environ["HW_PASSWORD"], session, "smoke-test"
        )

        assert await api.async_authenticate() is True, "authentication failed"
        print("auth: ok")

        locations = await api.async_get_locations()
        assert locations, "no locations returned"
        assert "id" in locations[0], "location shape changed: missing 'id'"
        print(f"locations: ok ({len(locations)})")

        devices_data = await api.async_get_devices(locations[0]["id"])
        assert devices_data and "errors" not in devices_data, "device query failed"
        devices = devices_data["data"]["home"]["devices"]
        watermeters = [d for d in devices if d.get("type") == "watermeter"]
        assert watermeters, "no watermeter device found on the account"

        device = watermeters[0]
        assert "identifier" in device
        assert "onlineState" in device
        print(f"devices: ok ({len(watermeters)} watermeter)")

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
        print(f"tsdb: ok ({len(stats['values'])} values)")


if __name__ == "__main__":
    if not (os.environ.get("HW_EMAIL") and os.environ.get("HW_PASSWORD")):
        sys.exit("HW_EMAIL/HW_PASSWORD not set")
    asyncio.run(main())
