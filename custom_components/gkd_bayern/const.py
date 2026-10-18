"""Constants for the GKD Bayern Wassertemperatur integration."""

from datetime import timedelta

DOMAIN = "gkd_bayern"
MANUFACTURER = "Gewässerkundlicher Dienst Bayern (LfU)"
NAME = "GKD Bayern Wassertemperatur"

CONF_STATIONS = "stations"
ATTR_STATION_ID = "station_id"
ATTR_RIVER = "river"
ATTR_DISTRICT = "district"
ATTR_REGION = "region"
ATTR_URL = "url"
ATTRIBUTION = "attribution"
ATTRIBUTION_TEXT = "Data source: LfU Bayern (gkd.bayern.de), CC BY 4.0"
ATTR_MEASURED_AT = "measured_at"
ATTR_LAST_MEASURED_AT = "last_measured_at"
ATTR_LAST_VALUE = "last_value"

DEFAULT_NAME = NAME

# The GKD website updates most stations every 15 minutes.
UPDATE_INTERVAL = timedelta(minutes=15)
# The latest measurement may be at most 1 hour old.
MAX_AGE = timedelta(hours=1)

BASE_URL = "https://www.gkd.bayern.de"
TABLES_URL = f"{BASE_URL}/de/fluesse/wassertemperatur/tabellen"

# Date format used on the website, e.g. "17.10.2026 18:00 Uhr"
TIMEZONE = "Europe/Berlin"
