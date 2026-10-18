"""Client and parsing helpers for the GKD Bayern website."""

from __future__ import annotations

from datetime import datetime
import re
from zoneinfo import ZoneInfo

import aiohttp
from bs4 import BeautifulSoup

from .const import MAX_AGE, TABLES_URL, TIMEZONE
from .data import Measurement, Station

# The GKD website rejects unknown user agents, so mimic a browser.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

_REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html",
    "Accept-Language": "de-DE,de;q=0.9",
}

# The bot protection serves reject pages with HTTP status 200, so the
# content has to be inspected for its marker as well.
_REJECTED_MARKER = "request rejected"

_STATION_RE = re.compile(
    r"/de/fluesse/wassertemperatur/(?P<region>[a-z_]+)/"
    r"[a-z0-9\-]+-(?P<id>\d+)/messwerte"
)
_DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}")
_TEMP_RE = re.compile(r"-?\d+[,.]\d+")
_TZ = ZoneInfo(TIMEZONE)


class GkdError(Exception):
    """Base error for the GKD Bayern integration."""


class GkdConnectionError(GkdError):
    """Connection to the GKD website failed."""


class GkdParseError(GkdError):
    """The GKD website returned unexpected content."""


class GkdApiClient:
    """Access the GKD Bayern website for station lists and measurements."""

    def __init__(self, session) -> None:
        """Initialize with an aiohttp ClientSession."""
        self._session = session

    async def _get(self, url: str) -> str:
        """Fetch a page and return its text."""
        try:
            async with self._session.get(url, headers=_REQUEST_HEADERS) as resp:
                resp.raise_for_status()
                text = await resp.text()
        except (TimeoutError, aiohttp.ClientError) as err:
            raise GkdConnectionError(f"Error fetching {url}: {err}") from err
        if _REJECTED_MARKER in text.casefold():
            raise GkdConnectionError(f"{url} was rejected by the website's bot protection")
        return text

    async def get_stations(self) -> dict[str, Station]:
        """Return all available stations keyed by their ID."""
        return parse_stations(await self._get(TABLES_URL))

    async def get_measurement(self, url: str) -> Measurement | None:
        """Fetch the newest measurement row from a station values page.

        Returns None if no parseable row was found. Freshness is checked
        by the caller.
        """
        return parse_measurement(await self._get(url))


def parse_stations(html: str) -> dict[str, Station]:
    """Parse the overview table into stations keyed by their ID."""
    soup = BeautifulSoup(html, "html.parser")
    stations: dict[str, Station] = {}

    for link in soup.select("table.tblsort ul.linkliste a[href*='messwerte']"):
        href: str = link.get("href", "")
        match = _STATION_RE.search(href)
        if not match:
            continue
        row = link.find_parent("tr")
        if row is None:
            continue
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        station = Station(
            id=match.group("id"),
            name=link.get_text(strip=True),
            river=cells[1].get_text(strip=True),
            district=cells[2].get_text(strip=True),
            url=href,
        )
        if not station.name or not station.river:
            continue
        stations[station.id] = station
    return stations


def parse_measurement(html: str) -> Measurement | None:
    """Parse the newest measurement row from a station values page."""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("table.tblsort tbody")
    if body is None:
        return None
    row = body.find("tr")
    if row is None:
        return None
    cells = row.find_all("td")
    if len(cells) < 2:
        return None
    date_text = cells[0].get_text(strip=True).replace("\xa0", " ")
    temp_text = cells[1].get_text(strip=True).replace("\xa0", " ")
    date_match = _DATE_RE.search(date_text)
    temp_match = _TEMP_RE.search(temp_text)
    if not date_match or not temp_match:
        return None
    measured_at = datetime.strptime(date_match.group(), "%d.%m.%Y %H:%M").replace(tzinfo=_TZ)
    return Measurement(
        temperature=float(temp_text.replace(",", ".")),
        measured_at=measured_at,
    )


def is_fresh(measurement: Measurement | None, now: datetime) -> bool:
    """Return True if the measurement is not older than one hour."""
    if measurement is None:
        return False
    now = now.replace(tzinfo=_TZ) if now.tzinfo is None else now.astimezone(_TZ)
    age = now - measurement.measured_at
    return age <= MAX_AGE


def now_berlin(now: datetime | None = None) -> datetime:
    """Return ``now`` in Europe/Berlin timezone."""
    if now is None:
        now = datetime.now(tz=_TZ)
    return now.astimezone(_TZ)
