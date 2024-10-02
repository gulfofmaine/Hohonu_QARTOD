import os
from datetime import datetime, timedelta
from typing import Optional, Union

import pandas as pd
import requests
from pydantic import BaseModel

DATE_FORMAT = "%Y-%m-%d"
FEET_TO_METERS = 0.3048
HOHONU_TIMEOUT = int(os.environ.get("HOHONU_TIMEOUT", 30))



class HohonuApi(BaseModel):
    """Access the Hohonu API

    API reference: https://hohonu.readme.io/reference/getting-started-with-your-api
    """

    api_key: str

    def headers(self):
        """Set up Hohonu API auth headers"""
        return {"Authorization": self.api_key}

    def load_daily_data(
        self,
        station_id: str,
        day: str,
        datum: str = "NAVD",
        cleaned: bool = True,
    ):
        """Load data for a given day based on YYYY-MM-DD string
        from https://dashboard.hohonu.io/api/v1/stations/{stationId}/statistic/

        API reference: https://hohonu.readme.io/reference/searchinventory
        """
        start_dt = datetime.strptime(day, DATE_FORMAT)
        end_dt = start_dt + timedelta(days=1)
        cleaned = "true" if cleaned else "false"

        url = (
            f"https://dashboard.hohonu.io/api/v1/stations/{station_id}/statistic/"
            f"?from={start_dt.strftime(DATE_FORMAT)}&to={end_dt.strftime(DATE_FORMAT)}"
            f"&datum={datum}&cleaned={cleaned}&format=json&tz=0"
        )

        response = requests.get(url, headers=self.headers(), timeout=HOHONU_TIMEOUT)
        response.raise_for_status()

        return response
    
    def fetch_data(
        self,
        start_date: str,
        end_date: str,
        station_id: str,
        cleaned: bool = False,
        datum: str = "NAVD",
    ):
        """Fetch Hohonu data for a given gauge and date range.

        Dates should be in YYYY-MM-DD.
        """
        DATE_FORMAT = "%Y-%m-%d"

        start_dt = datetime.strptime(start_date, DATE_FORMAT)
        end_dt = datetime.strptime(end_date, DATE_FORMAT)

        cleaned = "true" if cleaned else "false"

        url = (
            f"https://dashboard.hohonu.io/api/v1/stations/{station_id}/statistic/"
            f"?from={start_dt.strftime(DATE_FORMAT)}&to={end_dt.strftime(DATE_FORMAT)}"
            f"&datum={datum}&cleaned={cleaned}&format=json&tz=0"
        )

        response = requests.get(url, headers=self.headers(), timeout=HOHONU_TIMEOUT)
        response.raise_for_status()

        return DataResponse.model_validate_json(response.text)

    def station_info(self, station_id: str):
        """Load station info JSON from
        https://dashboard.hohonu.io/api/v1/stations/{station_id}

        API reference: https://hohonu.readme.io/reference/viewstation
        """
        url = f" https://dashboard.hohonu.io/api/v1/stations/{station_id}"

        response = requests.get(url, headers=self.headers(), timeout=HOHONU_TIMEOUT)
        response.raise_for_status()

        return StationInfo.model_validate_json(response.text)


class NoaaInfo(BaseModel):
    """Nearest NOAA station reading"""

    timestamp: list[str]
    name: Optional[str] = None
    data: list


class NoaaData(BaseModel):
    """Forecasted and navd88_meters data from nearest valid NOAA station"""

    observed: NoaaInfo
    prediction: NoaaInfo


class DataResponse(BaseModel):
    """Response from Hohonu API"""

    datum_type: str
    data: list[list[Union[str, float, None]]]
    last_reading: float
    last_update: str
    data_type: str
    noaa_data: NoaaData


def hohonu_response_to_df(response: DataResponse) -> pd.DataFrame:
    """Build a dataframe from a response from Hohonu"""
    df = pd.DataFrame(
        {
            "time": pd.to_datetime(response.data[0]),
            "navd88_meters": pd.Series(response.data[1]) * FEET_TO_METERS,  # Convert feet to meters
            "forecast": pd.Series(response.data[2]) * FEET_TO_METERS,  # Convert feet to meters
        },
    )

    forecast_na = df["forecast"].isna().all()

    if forecast_na:
        del df["forecast"]

    return df


class Distance(BaseModel):
    """Measurement"""

    unit: str
    value: float


class Subscribed(BaseModel):
    """Notification of station status"""

    phone_number: Optional[str] = None
    threshold_value: Optional[float] = None


class StationInfo(BaseModel):
    """Gauge station metadata from Hohonu API"""

    # access: bool
    custom_nearest_noaa: Optional[str] = None
    d2w_begin_caution: Optional[float] = None
    d2w_begin_emergency: Optional[float] = None
    decommissioned_date: Optional[str] = None
    distance: Distance
    download_permision: bool
    id: str
    images: Optional[list[str]] = None
    installation_date: Optional[datetime] = None
    latitude: float
    local_mllw: Optional[float] = None
    location: str
    longitude: float
    mhhw: Optional[float] = None
    mllw: Optional[float] = None
    mllw_begin_caution: Optional[float] = None
    mllw_begin_emergency: Optional[float] = None
    navd88: float
    navd88_begin_caution: Optional[float] = None
    navd88_begin_emergency: Optional[float] = None
    nearest_noaa_subordinate_observed: Optional[str] = None
    nearest_noaa_subordinate_prediction: Optional[str] = None
    nnoaa_station: Optional[str] = None
    organization: Optional[str] = None
    sensor: Optional[str] = None
    station_id: Optional[str] = None
    station_identifier: Optional[str] = None
    station_type: str
    status: str
    subscribed: Subscribed | bool = False
    tidal: bool
    uuid: str
    water: bool
