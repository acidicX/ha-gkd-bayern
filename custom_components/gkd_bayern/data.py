"""Typed data models for the GKD Bayern integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict


class StationConfig(TypedDict):
    """A configured station, stored in config entry data."""

    id: str
    name: str
    river: str
    district: str
    url: str


@dataclass(frozen=True)
class Station:
    """A measurement station from the overview table."""

    id: str
    name: str
    river: str
    district: str
    url: str

    @property
    def region(self) -> str:
        """Region slug of the URL, e.g. 'kelheim'."""
        return self.url.split("/wassertemperatur/")[1].split("/")[0]

    def as_config(self) -> StationConfig:
        """Return the config entry representation."""
        return StationConfig(
            id=self.id,
            name=self.name,
            river=self.river,
            district=self.district,
            url=self.url,
        )


@dataclass(frozen=True)
class Measurement:
    """The latest water temperature measurement of a station."""

    temperature: float
    measured_at: datetime
