# HomeWizard Cloud Watermeter Integration for Home Assistant

This is a custom integration for Home Assistant that allows you to retrieve daily consumption data from your HomeWizard watermeter devices via the HomeWizard Cloud API.

## Overview

The official [HomeWizard Energy](https://www.home-assistant.io/integrations/homewizard/) integration for Home Assistant provides excellent real-time data using a local API. However, for the **HomeWizard Watermeter**, this local API is only active when the device is powered by its USB port.

When the Watermeter runs on batteries, it disables the local API to conserve power. Instead, it takes four readings per day and uploads them to the HomeWizard cloud. This integration was created to bridge that gap, fetching those daily totals from the cloud and bringing them into Home Assistant.

## Who is this for?

This integration is specifically for users who:
- Own a HomeWizard Watermeter.
- Run it on **battery power** (and thus cannot use the local API).
- Want to integrate their daily water consumption data into Home Assistant.

If you power your Watermeter via USB, you should use the official **HomeWizard** integration for real-time data.

## Installation

The recommended way to install this integration is through the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

1.  Go to HACS > Integrations.
2.  Click the three dots in the top right and select "Custom repositories".
3.  Add the URL to this repository and select "Integration" as the category.
4.  Find "HomeWizard Cloud Watermeter" in the list and click "Install".
5.  Restart Home Assistant.

## Configuration

1.  Go to **Settings > Devices & Services**.
2.  Click **Add Integration** and search for "HomeWizard Cloud Watermeter".
3.  Enter your HomeWizard account email and password. These are the same credentials you use for the mobile app.
4.  If you have multiple homes configured in your account, select the correct location from the list of the second step.
5.  The integration will automatically discover your HomeWizard watermeter devices and create corresponding devices and sensor entities in Home Assistant.
6.  If you want to monitore your water usage, you can add the entity named "<Name of your Watermeter> Total Usage" to the water usage section of the Energy dashboard configuration.

## Important Notes

This integration relies on the HomeWizard Cloud. It is not real-time and will only update a few times a day, corresponding to when the battery-powered device uploads its data.

---

*This is an unofficial integration and is not affiliated with HomeWizard.*
