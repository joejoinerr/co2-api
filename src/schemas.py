"""API schemas."""

import datetime
from typing import Annotated

import pydantic


class ReadingBase(pydantic.BaseModel):
    """Base class for a reading."""

    co2_ppm: Annotated[int, pydantic.Field(gt=0, le=5000)]
    temp_celsius: Annotated[float, pydantic.Field(ge=-40.0, le=60.0)]
    pressure_mbar: Annotated[float, pydantic.Field(ge=700.0, le=1100.0)]


class Reading(ReadingBase):
    """A reading."""


class ReadingInDB(ReadingBase):
    """A reading in the database."""

    id: int
    recorded: datetime.datetime


class LatestReadings(pydantic.BaseModel):
    """Response containing the latest and average readings."""

    co2_ppm_latest: Annotated[int, pydantic.Field(gt=0)]
    co2_ppm_average_1h: Annotated[float, pydantic.Field(gt=0)]
    co2_ppm_average_1w: Annotated[float, pydantic.Field(gt=0)]
    last_reading_time: datetime.datetime
