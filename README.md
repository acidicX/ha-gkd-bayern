# GKD Bayern Wassertemperatur

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41CD52.svg)](https://github.com/hacs/integration)

Shows the current water temperature of measurement stations of the
[Gewässerkundlicher Dienst Bayern](https://www.gkd.bayern.de/de/fluesse/wassertemperatur/tabellen)
(Landesamt für Umwelt, Bavaria) in [Home Assistant](https://www.home-assistant.io) sensors.

> ⚠️ This integration uses the public website of the GKD. The values update every
> 15 minutes; the integration polls each configured station every 15 minutes and
> only accepts measurements younger than **1 hour**. Older values mark the
> sensor as _unavailable_, the last known value and measurement time stay in
> the entity attributes.

## Installation

### HACS (recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed.
2. Add this repository as a **custom repository** of category _Integration_:
   `https://github.com/acidicX/ha-gkd-bayern`
3. Install _GKD Bayern Wassertemperatur_.
4. Restart Home Assistant.

### Manual

Copy the folder `custom_components/gkd_bayern` into the `custom_components`
folder of your Home Assistant configuration and restart Home Assistant.

## Configuration

1. In Home Assistant, go to _Settings → Devices & Services_ and click
   **Add integration**, then choose **GKD Bayern Wassertemperatur**.
2. Select one or more measurement stations. The list is fetched live from
   gkd.bayern.de; every entry shows the station name and the river
   (e.g. _Augsburg Hochablaß (Lech)_).
3. The station list can be changed at any time via the options of the
   integration (click _Configure_ on the integration card): each ID listed
   there gets its own sensor and can be removed by deselecting it.

## Sensors

Every configured station creates one temperature sensor, named like the
station, grouped as a device per station. Entities provide these attributes:

| Attribute          | Description                                                |
| ------------------ | ---------------------------------------------------------- |
| `station_id`       | 8-digit GKD measurement site ID (e.g. `12004002`)          |
| `river`            | Gewässer (water body)                                      |
| `district`         | Landkreis (district code)                                  |
| `region`           | Region part of the GKD URL (e.g. `kelheim`)                |
| `measured_at`      | Timestamp of the shown value (ISO 8601)                    |
| `last_measured_at` | Time of the last accepted (≤1 h) value                     |
| `last_value`       | Last accepted value, kept when the sensor goes unavailable |
| `url`              | Source page of the data                                    |
| `attribution`      | Data source attribution                                    |

## License of the data

The data originates from the _Gewässerkundlicher Dienst Bayern_ by the
Bavarian Landesamt für Umwelt and is provided under the Creative Commons
Attribution 4.0 International license [(CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/legalcode.en). For more information, see the https://www.gkd.bayern.de/de/impressum.

## Branding

The integration is not yet listed in the
[Home Assistant brands](https://github.com/home-assistant/brands)
repository, so the HACS `brands` validation is skipped in CI (`ignore: brands`
in `validate.yaml`). To fix properly:

1. Run the [brands generation tool](https://brands.home-assistant.io/).
2. Submit a pull request to `home-assistant/brands` adding
   `data/custom_integrations/gkd_bayern.json` with the icon/logo/banner
   assets.
3. Once merged, remove `ignore: brands` from `.github/workflows/validate.yaml`.

## Troubleshooting

- The website may temporarily reject unusual clients (robot protection).
  If sensors stay _unavailable_, check the Home Assistant logs for
  `gkd_bayern` errors; the integration retries on the next cycle.
