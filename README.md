# HomeWizard Cloud Watermeter
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Home Assistant](https://img.shields.io/badge/home--assistant-2025.11+-blue.svg?style=for-the-badge&logo=home-assistant)
![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)

A custom Home Assistant integration to track your water consumption via the **HomeWizard Cloud**, designed specifically for their [battery-powered watermeter devices](https://www.homewizard.com/watermeter/).

> [!IMPORTANT]
> **TL;DR: Do you need this?**
> - :zap: **Don't have a Watermeter?** This is only for the Watermeter. Other HomeWizard devices work perfectly with the official integration.
> - :battery: **Running on Battery?** Yes, you need **this** integration.
> - :electric_plug: **Running on USB?** No, stop here! Use the [official HomeWizard Energy integration](https://www.home-assistant.io/integrations/homewizard/) for real-time local data.
---

## Why this integration?

The official [HomeWizard Energy](https://www.home-assistant.io/integrations/homewizard/) integration is amazing but has a limitation: it requires the **Local API**, which is disabled when the Watermeter runs on **batteries**.

**This integration bridges the gap:**
- :white_check_mark: Fetches data from the HomeWizard Cloud.
- :white_check_mark: Perfect for battery-powered setups (4 updates/day).
- :white_check_mark: High-resolution historical data (5-min intervals) injected into Long Term Statistics.
- :white_check_mark: Full Energy Dashboard support.

---

## Features

- **Device Support:** Automatically discovers all watermeter devices linked to your account.
- **Smart Tracking:** High-resolution consumption data (not just daily totals).
- **Diagnostics:** Monitor Online status and Wi-Fi signal strength.
- **Energy Dashboard:** Native integration with the Home Assistant Energy panel.
- **Auto-Sync:** Fetches the last 48h of data to ensure no drops, even if your Wi-Fi is flaky.

---

## Installation

### Option 1: HACS (Recommended)

The recommended way to install this integration is through the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

1. Open **HACS** > **Integrations**.
2. Search for `HomeWizard Cloud Watermeter` and **install** the integration.
3. **Restart** Home Assistant.

### Option 2: Manual

Copy the `custom_components/homewizard_cloud_watermeter` folder into your `config/custom_components` directory, then restart Home Assistant.

---

## Setup

1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for `HomeWizard Cloud Watermeter`.
3. Log in with your HomeWizard credentials.
5. **Energy Dashboard:** In the Water consumption section, search for "homewizard" entities and select the one corresponding to your device.

---

## Sensors provided

| Sensor | Enabled by default | Description |
| :--- | :--- | :--- |
| **Total Usage** | true | Water usage history (L) |
| **Last Device Sync** | true | Last time the device pushed its data to the cloud |
| **Wi-Fi Signal** | false | Wifi signal strength (%) |
| **Online State** | false | Whether the device was online recently or not |

---

## Community & Support

- **Found a bug?** Please open an [Issue](https://github.com/pyrech/homewizard_cloud_watermeter/issues).
- **Want to contribute?** Pull Requests are welcome!
- **Official Recognition:** While this is a community project, **HomeWizard** is aware of this integration and won't block it (see [Issue #2](https://github.com/pyrech/homewizard_cloud_watermeter/issues/2)).

---

## :warning: Disclaimer

*This is an unofficial community-driven integration. It is not affiliated with, authorized, or endorsed by HomeWizard.*
