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
