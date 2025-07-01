import os
from datetime import datetime, timedelta, date, time
from typing import Optional, Union

import pandas as pd
import requests
from pydantic import BaseModel


class Location(BaseModel):
    """Geographic coordinates"""
    latitude: float
    longitude: float

class Address(BaseModel):
    """Station address information"""
    county: str
    zip: str
    state: str
    city: str
    address_1: str
    address_2: Optional[str] = None

class StationInfo(BaseModel):
    """Greenstream station information"""
    location: Location
    device: str
    address: Address
    lastUpdate: datetime
    name: str
    enabled: bool
    active: bool
    createDate: datetime
    description: str
    id: str


class GreenstreamApi(BaseModel):
    """Access the Greenstream API

    API reference: https://docs.greenstream.cloud/api/index.html
    """

    api_key: str

    def headers(self):
        """Set up Greenstream API headers"""
        return {"x-api-key": self.api_key}
    
    def station_info(self, station_id: str) -> StationInfo:
        """Load station info JSON from
        https://dashboard.hohonu.io/api/v1/stations/{station_id}
        """
        url = f"https://api.greenstream.cloud/site/?id={station_id}"
        headers = self.headers()
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return StationInfo.model_validate_json(response.text)

    def fetch_data(
        self,
        site_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
    ) -> pd.DataFrame:
        """Fetch data from Greenstream API"""
        url = f"https://api.greenstream.cloud/site/messages?id={site_id}&start={int(start_datetime.timestamp())}&end={int(end_datetime.timestamp())}"
        headers = self.headers()

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        df =  pd.DataFrame((flatten_greenstream_message(d) for d in response.json()))
        df = df.rename(columns={"timestamp": "time"})
        return df


def flatten_greenstream_message(d):
    return {
        "timestamp": pd.Timestamp.fromtimestamp(d["timestamp"]),
        **d["senix"],
        **d["ina219"],
        **d["lte"],
        "id": d["id"],
        "device": d["device"]
    }


def load_greenstream_data_and_config():
    import streamlit as st

    config = {}

    try:
        api_key = st.secrets["GREENSTREAM_API_KEY"]
    except KeyError:
        api_key = st.text_input(
            "Greenstream API key",
            type="password",
            help="Please enter your Greenstream API key."
        )

    if api_key is None or api_key == "":
        st.error("No Greenstream API key found. Please add to [.streamlit/secrets.toml](https://docs.streamlit.io/develop/concepts/connections/secrets-management), environment variables, or enter in the input box.")
        st.stop()


    api = GreenstreamApi(api_key=api_key)

    @st.cache_data
    def load_station_info(station_id: str):
        """Load station info from Greenstream API"""
        return api.station_info(station_id)
    
    # @st.cache_data
    def load_data(station_id: str, start_date: date, end_date: date) -> pd.DataFrame:
        """Load data from Greenstream API"""
        return api.fetch_data(
            site_id=station_id,
            start_datetime=datetime.combine(start_date, time(0, 0, 0)),
            end_datetime=datetime.combine(end_date, time(23, 59, 59))
        )
    
    with st.sidebar:
        with st.expander("Station selector", expanded=True):
            station_id = st.text_input(
                "Greenstream site ID",
                help="The ID of the site in Greenstream dashboard."
            )

        if not station_id:
            st.error("Please enter a valid Greenstream site ID.")
            st.stop()

        station_info = load_station_info(station_id)
        
        # st.write(station_info)

        st.markdown(f"""
        ## {station_info.name}

        - Latitude: {station_info.location.latitude}
        - Longitude: {station_info.location.longitude}
        - Install date: {station_info.createDate}
        """)
        config.update({
            "site_id": station_id,
            "latitude": station_info.location.latitude,
            "longitude": station_info.location.longitude,
            "start_date": station_info.createDate.isoformat(),
        })
    
        with st.expander("Data selector", expanded=True):
            now = datetime.now()
            week_ago = now - timedelta(days=7)

            date_range = st.date_input(
                "Date range",
                (week_ago, now),
                max_value=now,
                min_value=station_info.createDate,
                help="Date range to load testing data for."
            )

            too_long = date_range[1] - date_range[0] > timedelta(days=30)
            if too_long:
                st.warning("Please select a data range of less than 30 days.")

            navd88_elevation_meters = st.number_input(
                "Elevation of station above NAVD88 (meters)",
                value=0,
                help="Elevation of the station above NAVD88 in meters."
            )

            config.update({
                "navd88_elevation_meters": navd88_elevation_meters,
            })

            load_data_button = st.toggle("Load data", disabled=too_long)

    if not load_data_button:
        st.warning("Please select a date range and click 'Load data' to fetch data from Greenstream.")
        st.stop()

    data = load_data(station_id, date_range[0], date_range[1])
    data["navd88_meters"] = navd88_elevation_meters - (data["mm"] / 1_000)

    return data, config
