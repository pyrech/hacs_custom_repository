"""Tests for the statistics injection logic of the coordinator."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import current_entry
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.homewizard_cloud_watermeter.const import DOMAIN
from custom_components.homewizard_cloud_watermeter.coordinator import (
    HomeWizardCloudDataUpdateCoordinator,
)

DEVICE = {
    "identifier": "water/ABC",
    "sanitized_identifier": "water_abc",
    "name": "Water",
}
STAT_ID = f"{DOMAIN}:water_abc_total"


def make_coordinator(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    current_entry.set(entry)
    return HomeWizardCloudDataUpdateCoordinator(hass, api=SimpleNamespace(), home_id=1)


def hour(days_ago: int, hour_of_day: int):
    """An hour-aligned UTC datetime in the past."""
    base = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    return base - timedelta(days=days_ago) + timedelta(hours=hour_of_day - base.hour)


def entries(usage_by_hour: dict):
    """Build TSDB-like value entries, one 15m point per hour."""
    return [
        {"time": start.isoformat(), "water": usage}
        for start, usage in usage_by_hour.items()
    ]


async def inject(hass, coordinator, usage_by_hour: dict):
    total = await coordinator.async_inject_cleaned_stats(entries(usage_by_hour), DEVICE)
    await async_wait_recording_done(hass)
    return total


async def get_rows(hass):
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        dt_util.utcnow() - timedelta(days=30),
        None,
        {STAT_ID},
        "hour",
        None,
        {"state", "sum"},
    )
    return [
        (dt_util.utc_from_timestamp(row["start"]), row["state"], row["sum"])
        for row in stats.get(STAT_ID, [])
    ]


async def test_first_import(recorder_mock, hass):
    coordinator = make_coordinator(hass)
    h0, h1 = hour(1, 10), hour(1, 11)

    total = await inject(hass, coordinator, {h0: 10.0, h1: 20.0})

    assert total == 30.0
    assert await get_rows(hass) == [(h0, 10.0, 10.0), (h1, 20.0, 30.0)]


async def test_partial_hour_is_completed_on_next_poll(recorder_mock, hass):
    """The original drift bug: an hour recorded partially must be updated."""
    coordinator = make_coordinator(hass)
    h0, h1 = hour(1, 10), hour(1, 11)

    await inject(hass, coordinator, {h0: 5.0})
    total = await inject(hass, coordinator, {h0: 12.0, h1: 3.0})

    assert total == 15.0
    assert await get_rows(hass) == [(h0, 12.0, 12.0), (h1, 3.0, 15.0)]


async def test_reimport_past_day_shifts_later_sums(recorder_mock, hass):
    """import_day: rewriting a past day keeps later day totals consistent."""
    coordinator = make_coordinator(hass)
    day2, day1 = hour(2, 10), hour(1, 10)

    await inject(hass, coordinator, {day2: 10.0, day1: 20.0})
    total = await inject(hass, coordinator, {day2: 15.0})

    assert total == 35.0
    assert await get_rows(hass) == [(day2, 15.0, 15.0), (day1, 20.0, 35.0)]


async def test_zero_hours_skipped_beyond_but_corrected_inside(recorder_mock, hass):
    coordinator = make_coordinator(hass)
    h0, h1, h2 = hour(1, 10), hour(1, 11), hour(1, 12)

    await inject(hass, coordinator, {h0: 10.0, h1: 0.0, h2: 7.0})
    assert await get_rows(hass) == [(h0, 10.0, 10.0), (h2, 7.0, 17.0)]

    # Cloud revision zeroes out h0: inside the recorded region, zero rows
    # must be written so the stale value gets corrected.
    total = await inject(hass, coordinator, {h0: 0.0, h1: 0.0, h2: 7.0})

    assert total == 7.0
    assert await get_rows(hass) == [(h0, 0.0, 0.0), (h1, 0.0, 0.0), (h2, 7.0, 7.0)]


async def test_gap_keeps_sum_continuity(recorder_mock, hass):
    """Device offline for days: new data continues from the last known sum."""
    coordinator = make_coordinator(hass)
    old, recent = hour(5, 10), hour(1, 10)

    await inject(hass, coordinator, {old: 10.0})
    total = await inject(hass, coordinator, {recent: 7.0})

    assert total == 17.0
    assert await get_rows(hass) == [(old, 10.0, 10.0), (recent, 7.0, 17.0)]


def cloud_device(online_state: str):
    return {
        "identifier": "water/ABC",
        "type": "watermeter",
        "name": "Water",
        "onlineState": online_state,
    }


def make_cloud_coordinator(hass, device: dict):
    coordinator = make_coordinator(hass)
    coordinator.api = SimpleNamespace(
        async_get_devices=AsyncMock(
            return_value={"data": {"home": {"devices": [device]}}}
        ),
        async_get_tsdb_data=AsyncMock(return_value={"values": []}),
    )
    return coordinator


async def test_offline_device_creates_notification_once(recorder_mock, hass):
    device = cloud_device("OFFLINE")
    coordinator = make_cloud_coordinator(hass, device)

    with patch(
        "custom_components.homewizard_cloud_watermeter.coordinator.async_create"
    ) as create:
        await coordinator._async_update_data()
        # A second poll while still offline must not notify again
        await coordinator._async_update_data()

    assert create.call_count == 1
    assert (
        create.call_args.kwargs["notification_id"]
        == "homewizard_watermeter_offline_water_abc"
    )


async def test_back_online_dismisses_notification(recorder_mock, hass):
    device = cloud_device("OFFLINE")
    coordinator = make_cloud_coordinator(hass, device)

    with (
        patch(
            "custom_components.homewizard_cloud_watermeter.coordinator.async_create"
        ) as create,
        patch(
            "custom_components.homewizard_cloud_watermeter.coordinator.async_dismiss"
        ) as dismiss,
    ):
        await coordinator._async_update_data()
        device["onlineState"] = "ONLINE_RECENTLY"
        await coordinator._async_update_data()

        # Going offline again must notify again
        device["onlineState"] = "OFFLINE"
        await coordinator._async_update_data()

    assert create.call_count == 2
    dismiss.assert_called_once_with(
        hass, notification_id="homewizard_watermeter_offline_water_abc"
    )


async def test_online_device_never_notifies(recorder_mock, hass):
    coordinator = make_cloud_coordinator(hass, cloud_device("ONLINE_RECENTLY"))

    with (
        patch(
            "custom_components.homewizard_cloud_watermeter.coordinator.async_create"
        ) as create,
        patch(
            "custom_components.homewizard_cloud_watermeter.coordinator.async_dismiss"
        ) as dismiss,
    ):
        await coordinator._async_update_data()

    create.assert_not_called()
    dismiss.assert_not_called()
