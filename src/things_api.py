from datetime import datetime, date, timedelta, time
import os

import pandas as pd
from pydantic import BaseModel
import requests


THINGS_TIMEOUT = int(os.environ.get("THINGS_TIMEOUT", 30))

URL_PATTERN = '{domain}/api/v3/as/applications/{application_id}/devices/{device_id}/packages/storage/uplink_message'


class ThingsApi(BaseModel):
    """Access the Thing Network API

    Storage API reference: https://www.thethingsindustries.com/docs/integrations/storage/retrieve/
    """

    api_key: str
    account_id: str
    application_id: str
    region: str

    def headers(self):
        """Set up The Things Network API headers"""
        return {"Authorization": f"Bearer {self.api_key}"}
    

    def fetch_segment(
            self,
            device_id: str,
            start_datetime: datetime,
            end_datetime: datetime,
    ):
        """Fetch a shorter chunk of time"""
        url = (
            f"https://{self.account_id}.{self.region}.cloud.thethings.industries/api/v3/as/applications/"
            f"{self.application_id}/devices/{device_id}/packages/storage/uplink_message"
        )
        headers = {
            **self.headers(),
            "Accept": "text/event-stream"
        }
        params = {
            "after": f"{start_datetime.isoformat()}Z",
            "before": f"{end_datetime.isoformat()}Z",
            "field_mask": "up.uplink_message.decoded_payload"
        }
        response = requests.get(url, params=params, headers=headers, timeout=THINGS_TIMEOUT)
        try:
            response.raise_for_status()
        except Exception as e:
            print(response.text)
            raise e

        df = pd.DataFrame(Data.lines_to_dicts(response.text))
        return df


    def fetch_data(
        self,
        device_id: str,
        start_date: date,
        end_date: date,
        navd88_elevation_meters: float,
    ):
        """Fetch The Things Network from the storage API given a date range"""

        dfs = []

        for (start, end) in generate_time_periods(start_date, end_date):
            df = self.fetch_segment(device_id, start, end)
            dfs.append(df)

        df = pd.concat(dfs, ignore_index=True)

        df["time"] = df["recieved_at"]
        df["navd88_meters"] = navd88_elevation_meters - (df["distance"] / 1_000)

        return df




class DeviceId(BaseModel):
    device_id: str

class DecodedPayload(BaseModel):
    battery: float
    distance: int
    sdError: int

class UplinkMessage(BaseModel):
    received_at: datetime
    decoded_payload: DecodedPayload

class Result(BaseModel):
    end_device_ids: DeviceId
    received_at: datetime
    uplink_message: UplinkMessage

class Data(BaseModel):
    result: Result

    def flatten(self):
        return {
            "recieved_at": self.result.uplink_message.received_at,
            "battery": self.result.uplink_message.decoded_payload.battery,
            "distance": self.result.uplink_message.decoded_payload.distance,
            "sd_error": self.result.uplink_message.decoded_payload.sdError
        }

    @classmethod
    def lines_to_dicts(cls, text: str):
        for line in text.splitlines():
            if line != "":
                yield cls.model_validate_json(line).flatten()

def generate_time_periods(start_date: date, end_date: date):
    """Generate a list of time periods to fetch data for"""
    current_date = datetime.combine(start_date, time.min)
    end_date = datetime.combine(end_date, time.max)

    while current_date < end_date:
        next_date = current_date + timedelta(hours=6)
        # print((current_date, next_date))
        yield (current_date, next_date)
        current_date = next_date


def load_things_streamlit_data_and_config():
    import streamlit as st

    config = {}

    try:
        api_key = st.secrets["THINGS_API_KEY"]
    except KeyError:
        api_key = st.text_input(
            "Things network API key",
            type="password",
            help="""
        Please enter your Things Network API key. It can be retrieved from
        API Keys which is avaliable underneath the Applications tab of the dashboard.
        """
        )

    if api_key is None or api_key == "":
        st.error("No The Things Network API key found. Please add to [.streamlit/secrets.toml](https://docs.streamlit.io/develop/concepts/connections/secrets-management), environment variables, or enter in the input box.")
        st.stop()

    api = ThingsApi(api_key=api_key, account_id="neracoos", application_id="providence-wl", region="nam1")

    @st.cache_data
    def fetch_data(device_id: str, start_date: date, end_date: date, navd88_elevation_meters: float,):
        """Load device info from The Things Network"""
        df = api.fetch_data(device_id, start_date, end_date, navd88_elevation_meters)
        return df


    with st.sidebar:
        with st.expander("Station selector", expanded=True):
            station_id = st.text_input(
                "Things device ID",
                # value="brown-wl-012",
                help="""
                The ID of the device in The Things Network console.
                """
            )

            if station_id == "":
                st.warning(
                    "Please enter a device ID. It can be found in The Things Network console."
                )
                st.stop()

            latitude = st.number_input("Station Latitude (decimal degrees)")
            longitude = st.number_input("Station longitude (decimal degrees)")
            navd88_elevation_meters = st.number_input("Elevation of station above navd88_meters")
            install_date = st.date_input("Install date")

            config.update({
                "device_id": station_id,
                "latitude": latitude,
                "longitude": longitude,
                "navd88_elevation_meters": navd88_elevation_meters,
                "start_date": install_date.isoformat(),
            })

    with st.sidebar:
        with st.expander("Data selector", expanded=True):
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            date_range = st.date_input(
                "Date range",
                (week_ago, now),
                max_value=now,
                min_value=month_ago,
                help="Date range to load testing data for (up to a max of a month ago)"
            )

            load_data_button = st.toggle("Load data")
    
    if not load_data_button:
        st.warning("Please select a date range and toggle 'Load data' to start generating QARTOD config")
        st.stop()

    data = fetch_data(station_id, date_range[0], date_range[1], navd88_elevation_meters)

    return data, config