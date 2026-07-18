from datetime import timedelta, datetime
import logging

from homeassistant.components.persistent_notification import DOMAIN as NOTIFY_DOMAIN
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData,
    StatisticMeanType,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.persistent_notification import async_create, async_dismiss
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.const import UnitOfVolume

from .const import DOMAIN
from .api import HomeWizardCloudApi

_LOGGER = logging.getLogger(__name__)

class HomeWizardCloudDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api: HomeWizardCloudApi, home_id: int):
        self.api = api
        self.home_id = home_id
        self._pending_stats = None
        self._offline_devices = set()
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=60),
        )

    async def _async_update_data(self):
        if "recorder" not in self.hass.config.components:
            _LOGGER.debug("Recorder not loaded, skipping update.")
            return {}

        devices_data = await self.api.async_get_devices(self.home_id)
        if not devices_data:
            raise UpdateFailed(f"Error fetching HomeWizard devices.")

        if "errors" in devices_data:
            raise UpdateFailed(f"Error fetching HomeWizard devices: {devices_data.get('errors')}")

        devices = devices_data.get("data", {}).get("home", {}).get("devices", [])

        now = dt_util.now()
        yesterday = now - timedelta(days=1)

        data = {}

        # Find watermeter devices and fetch their data
        for device in devices:
            if device.get("type") != "watermeter":
                continue

            _LOGGER.debug("Found HomeWizard watermeter device '%s', fetching data.", device["identifier"])

            # Sanitize the identifier for Home Assistant's use
            # This will be used for statistic_id, unique_id, and device_id
            device['sanitized_identifier'] = device["identifier"].replace('/', '_')

            # Retrieve device data
            stats_today = await self.api.async_get_tsdb_data(now, self.hass.config.time_zone, device["identifier"])
            stats_yesterday = await self.api.async_get_tsdb_data(yesterday, self.hass.config.time_zone, device["identifier"])

            if not stats_today or "values" not in stats_today:
                _LOGGER.warning("No data received for watermeter device.")
                continue

            if not stats_yesterday or "values" not in stats_yesterday:
                _LOGGER.warning("No yesterday data received for watermeter device.")
                continue

            combined_values = stats_yesterday.get("values", []) + stats_today.get("values", [])

            total = await self.async_inject_cleaned_stats(combined_values, device)

            last_sync_at = None

            for entry in reversed(combined_values):
                if entry.get("water") is not None:
                    last_sync_at = dt_util.parse_datetime(entry["time"])
                    break

            data[device['sanitized_identifier']] = ({
                "total": total,
                "unit": UnitOfVolume.LITERS,
                "device": device,
                "last_sync_at": last_sync_at,
            })

            # Check and handle online state changes
            online_state = device.get("onlineState", "Unknown")
            device_name = device.get("name", "Watermeter")
            sanitized_identifier = device['sanitized_identifier']

            if online_state == "OFFLINE" and sanitized_identifier not in self._offline_devices:
                self._offline_devices.add(sanitized_identifier)
                async_create(
                    self.hass,
                    f"Watermeter device {device_name} is offline. Please check if the batteries need to be replaced.",
                    title="HomeWizard Watermeter",
                    notification_id=f"homewizard_watermeter_offline_{sanitized_identifier}"
                )
            elif online_state == "ONLINE_RECENTLY" and sanitized_identifier in self._offline_devices:
                self._offline_devices.remove(sanitized_identifier)
                async_dismiss(
                    self.hass,
                    notification_id=f"homewizard_watermeter_offline_{sanitized_identifier}"
                )

        return data

    async def async_import_day(self, date):
        """Re-fetch and re-inject statistics for a single day."""
        day = datetime.combine(date, datetime.min.time())

        for info in (self.data or {}).values():
            device = info["device"]

            stats = await self.api.async_get_tsdb_data(day, self.hass.config.time_zone, device["identifier"])
            if not stats or "values" not in stats:
                _LOGGER.warning("No data received for device '%s' on %s, skipping.", device["identifier"], date)
                continue

            _LOGGER.info("Re-importing statistics for device '%s' on %s.", device["identifier"], date)
            await self.async_inject_cleaned_stats(stats.get("values", []), device)

    async def async_inject_cleaned_stats(self, values: list, device: dict):
        """Clean data and inject into HA statistics, rewriting the fetched window.

        Rows already recorded inside the window are updated in place (the
        recorder overwrites external statistics sharing the same start), so
        the partially-recorded current hour and late-arriving cloud revisions
        get corrected on the next poll instead of being lost.
        """
        statistic_id = f"{DOMAIN}:{device['sanitized_identifier']}_total"

        metadata = StatisticMetaData(
            has_sum=True,
            name=f"{device.get('name')} Total",
            source=DOMAIN,
            statistic_id=statistic_id,
            unit_of_measurement=UnitOfVolume.LITERS,
            unit_class=SensorDeviceClass.VOLUME,
            mean_type=StatisticMeanType.NONE,
        )

        hourly_data = {}
        for entry in values:
            # Ignore nulls (mainly future hours)
            if entry.get("water") is None:
                continue

            time = dt_util.parse_datetime(entry["time"])
            if not time:
                continue

            hour_timestamp = dt_util.as_utc(time.replace(minute=0, second=0, microsecond=0))

            # Security: don't process data far in the future
            if hour_timestamp > dt_util.utcnow() + timedelta(hours=1):
                continue

            if hour_timestamp not in hourly_data:
                hourly_data[hour_timestamp] = 0.0
            hourly_data[hour_timestamp] += float(entry["water"])

        # Get the absolute last point in history to ensure continuity
        last_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, statistic_id, True, {"sum"}
        )

        last_sum = 0.0
        last_stat_time = None

        if statistic_id in last_stats and last_stats[statistic_id]:
            point = last_stats[statistic_id][0]
            last_sum = point.get("sum") or 0.0

            raw_start = point.get("start")
            if raw_start is not None:
                if isinstance(raw_start, (int, float)):
                    last_stat_time = dt_util.utc_from_timestamp(raw_start)
                else:
                    last_stat_time = dt_util.as_utc(raw_start)

        if not hourly_data:
            # Always register the metadata, even with no data points, so the
            # statistic is immediately selectable in the Energy dashboard.
            async_add_external_statistics(self.hass, metadata, [])
            return last_sum

        window_start = min(hourly_data)
        window_end = max(hourly_data) + timedelta(hours=1)

        # Existing rows from the window start onward: used to rebase the
        # cumulative sum before the window, and to shift the rows recorded
        # after the window when a past day is re-imported.
        existing_rows = []
        if last_stat_time is not None and last_stat_time >= window_start:
            existing = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period,
                self.hass,
                window_start,
                None,
                {statistic_id},
                "hour",
                None,
                {"state", "sum"},
            )
            existing_rows = existing.get(statistic_id) or []

        # Baseline: cumulative sum just before the fetched window, i.e. the
        # first existing row's sum minus its own state.
        baseline_sum = last_sum
        if existing_rows:
            baseline_sum = (existing_rows[0].get("sum") or 0.0) - (existing_rows[0].get("state") or 0.0)

        in_window = [r for r in existing_rows if r["start"] < window_end.timestamp()]
        after_window = [r for r in existing_rows if r["start"] >= window_end.timestamp()]

        stat_data = []
        cumulative_sum = baseline_sum

        for hour in sorted(hourly_data.keys()):
            usage = hourly_data[hour]

            # Skip empty hours beyond what is already recorded; inside the
            # rewritten region keep them so stale rows get corrected.
            if usage == 0 and (last_stat_time is None or hour > last_stat_time):
                continue

            cumulative_sum += usage

            stat_data.append(
                StatisticData(
                    start=hour,
                    state=usage,
                    sum=cumulative_sum
                )
            )

        # If rows exist after the window (past-day re-import), shift their
        # sums by the delta introduced by the rewrite to keep continuity.
        old_sum_at_window_end = in_window[-1]["sum"] if in_window else baseline_sum
        delta = cumulative_sum - (old_sum_at_window_end or 0.0)
        if delta:
            for row in after_window:
                stat_data.append(
                    StatisticData(
                        start=dt_util.utc_from_timestamp(row["start"]),
                        state=row.get("state") or 0.0,
                        sum=(row.get("sum") or 0.0) + delta,
                    )
                )

        async_add_external_statistics(self.hass, metadata, stat_data)

        return cumulative_sum if not after_window else (after_window[-1].get("sum") or 0.0) + delta
