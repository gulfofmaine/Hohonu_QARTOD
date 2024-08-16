from datetime import datetime, timedelta

import streamlit as st

from hohonu_api import HohonuApi, DATE_FORMAT, hohonu_response_to_df
import qc_helpers

FEET_TO_METERS = 0.3048

st.markdown("""
# Hohonu dataset QARTOD and config generation

This tool is to help generate QARTOD configuration files
for Hohonu gauges deployed for NERACOOS.

Testing range suggestions developed in coordination with
Hannah Baranes.   
""")

try:
    api_key = st.secrets["HOHONU_API_KEY"]
except KeyError:
    api_key = st.text_input(
        "Hohonu API key",
        type="password",
        help="""
Please enter your Hohonu API key. It can be retrieved from
https://dashboard.hohonu.io/profile
""",
    )

if api_key is None or api_key == "":
    st.error(
        "No Hohonu API key found. Please add to [.streamlit/secrets.toml](https://docs.streamlit.io/develop/concepts/connections/secrets-management), environment variables, or enter in the input box."
    )
    st.stop()

api = HohonuApi(api_key=api_key)


@st.cache_data
def load_station_info(station_id: str):
    """Load station info JSON from
    https://dashboard.hohonu.io/api/v1/stations/{station_id}
    """
    response = api.station_info(station_id)
    return response


@st.cache_data
def fetch_data(station_id: str, date_range: tuple[datetime, datetime]):
    """Load data for a given day based on YYYY-MM-DD string
    from https://dashboard.hohonu.io/api/v1/stations/{stationId}/statistic/"""

    response = api.fetch_data(
        start_date=date_range[0].strftime(DATE_FORMAT),
        end_date=date_range[1].strftime(DATE_FORMAT),
        station_id=station_id,
        cleaned=True,
        datum="NAVD",
    )
    df = hohonu_response_to_df(response)
    return df


with st.sidebar:
    with st.expander("Station Selector", expanded=True):
        station_id = st.text_input(
            "Station ID",
            value="hohonu-180",
            help="""
    To get the station ID, find the station in the [Hohonu dashboard](https://dashboard.hohonu.io/),
    then select the segment between `map-page/` and it's name.

    For example `hohonu-180` for `https://dashboard.hohonu.io/map-page/hohonu-180/ChebeagueIsland,Maine`.
    """,
        )

        station_info = load_station_info(station_id)

        st.markdown(f"""
        {station_info.location}

        - Latitude: {station_info.latitude}
        - Longitude: {station_info.longitude}
        - NAVD88: {station_info.navd88}
        - Install date: {station_info.installation_date}
        """)

with st.sidebar:
    with st.expander("Data selector", expanded=True):
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        date_range = st.date_input(
            "Date range",
            (week_ago, now),
            max_value=now,
            min_value=station_info.installation_date,
            help="""
                Date range to load testing data for.
                """,
        )

        too_long = date_range[1] - date_range[0] > timedelta(days=30)
        if too_long:
            st.warning(
                "Please select a date range of less than 30 days. "
                "This is to prevent the API from timing out."
            )

        load_data_button = st.toggle("Load data", disabled=too_long)

if not load_data_button:
    st.warning(
        "Please select a date range and toggle 'Load data' to generate QARTOD config."
        ""
    )
    st.stop()


data = fetch_data(station_id, date_range)

with st.expander("Loaded data"):
    st.dataframe(data)
    st.line_chart(data, x="time", y="observed", y_label="NAVD88 (m)")

with st.sidebar:
    with st.expander("Datum selector", expanded=True):
        st.markdown("""
                    
    Datums should be entered as offsets from NAVD88.

    They can either be entered from known values,
    or can be calculated using [CO-OPS Tidal Analysis Datum Calculator](https://access.co-ops.nos.noaa.gov/datumcalc/).
                    
    For calculation, at least a month's worth of clean data is required.
    """)

        mhhw = st.number_input(
            "Mean High High Water (MHHW meters)",
            # value=station_info.mhhw,
            help="""
            The mean high high water (MHHW) datum offset for the gauge in meters from NAVD88.datum for the gauge.
            """,
        )

        mllw = st.number_input(
            "Mean Low Low Water (MLLW meters)",
            # value=station_info.mllw,
            help="""
            The mean low low water (MLLW) datum offset for the gauge in meters from NAVD88.
            """,
        )


with st.expander("Gross range test", expanded=True):
    with st.popover("Test configuration suggestions"):
        st.markdown("""
        ### Gross range test configuration for Gulf of Maine (not New England Shelf)

        #### Suspect Limits

        For stations with tidal datums (might not want this approach because it will always take a while to get tidal datums, and tidal datums change):  
        - Upper limit of range: MHHW + 6 ft  
        - Lower limit of range: MLLW – 4.5 ft  

        

        For stations without tidal datums:  
        - If there are no tidal datums because the station was just installed: use VDatum to get MHHW and MLLW relative to NAVD88 at a point close to the sensor, and use the same upper and lower limits   
            - Note: if it’s a station with river influence (like Bath), it might require some local expertise to set the limits. A solid approach is just taking the HW and LW measured over the course of the first week, and using something like HW + 10 ft and LW – 10 ft to be conservative  
        - If there are no tidal datums because the sensor bottoms out at low tide:  
            - Lower limit: Use the dry bottom elevation  
            - Upper limit: Use VDatum MHHW + 6 ft

                                    
        #### Fail upper and lower limits
        - Upper limit: distance to water is less than whatever the minimum sensing range is  
        - Lower limit: either hard bottom (if it’s a site that bottoms out at LW, or if we have a depth measurement at the site), or distance to water = maximum of sensing range  
                    
        #### Notes  

        Top recorded water levels, in ft MHHW (and year)  
        - Gulf of Maine 
            - Eastport: 5.07 (2020)  
            - Bar Harbor: 4.43 (2024) 
            - Portland: 4.67 (2024) 
            - Boston: 4.89 (2018) 
        - New England Shelf 
            - Chatham, MA: 4.28 (2014)  
            - Newport, RI: 9.45 (1938)
            -New London, CT: 7.53 (1938) 

        Lowest observed  
        - Eastport: -3.46 ft MLLW  (this will have the largest variability)  
        """)

    gross_col_1, gross_col_2 = st.columns([1, 3])

    with gross_col_1:
        st.markdown("##### Suspect span")

        gross_suspect_upper_limit = st.number_input(
            "Upper limit",
            value=mhhw + 6 * FEET_TO_METERS,
            help="""
            The upper limit of the gross range test.
            """,
        )

        gross_suspect_lower_limit = st.number_input(
            "Lower limit",
            value=mllw - 4.5 * FEET_TO_METERS,
            help="""
            The lower limit of the gross range test.
            """,
        )

        st.markdown("##### Fail span")

        gross_fail_upper_limit = st.number_input(
            "Upper limit",
            # value=0,
            help="""
            The upper limit of the gross range test.
            """,
        )

        gross_fail_lower_limit = st.number_input(
            "Lower limit",
            # value=0,
            help="""
            The lower limit of the gross range test.
            """,
        )

        gross_range_test_toggle = st.toggle("Enable Gross range test", value=True)

    with gross_col_2:
        if not gross_range_test_toggle:
            st.write("Gross range test is disabled.")
        else:
            gross_range_test_config = {
                "gross_range_test": {
                    "suspect_span": [gross_fail_lower_limit, gross_fail_upper_limit],
                    "fail_span": [gross_fail_lower_limit, gross_fail_upper_limit],
                }
            }
            gross_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        "observed": {
                            "qartod": gross_range_test_config,
                        }
                    }
                ),
            )

            plot = qc_helpers.plot_results(
                gross_df,
                "gross_range_test",
                title="Gross range test",
            )
            st.bokeh_chart(plot, use_container_width=True)

            with st.popover("Tabular results"):
                st.dataframe(gross_df)

with st.expander("Rate of change test", expanded=True):
    with st.popover("Test configuration suggestions"):
        st.markdown("""
### Rate of change test. Input as a rate.  

- Suspect: 0.75 feet per 6 minutes  
- Fail: 1 foot per 6 minutes  

Rationale: max rate of change from tides in Eastport is 5.3 ft per hour (midtide on 1/13/2024), or ~0.5 ft per 6 minutes. Add 0.25 feet for a sustained wind-driven increase in water level.  

May want to adjust this so it’s dependent on tidal range  
                    """)

    rate_col_1, rate_col_2 = st.columns([1, 3])

    with rate_col_1:
        rate_threshold = st.number_input(
            "Rate threshold",
            value=0.75 * FEET_TO_METERS,
            format="%.3f",
            help="""
            The rate of change threshold for the rate of change test.
            """,
        )
        rate_of_change_test_toggle = st.toggle("Enable Rate of change test", value=True)

    with rate_col_2:
        if not rate_of_change_test_toggle:
            st.write("Rate of change test is disabled.")
        else:
            rate_of_change_test_config = {
                "rate_of_change_test": {
                    "threshold": rate_threshold,
                }
            }
            rate_of_change_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        "observed": {
                            "qartod": rate_of_change_test_config,
                        }
                    }
                ),
            )

            plot = qc_helpers.plot_results(
                rate_of_change_df,
                "rate_of_change_test",
                title="Rate of change test",
            )
            st.bokeh_chart(plot, use_container_width=True)
            with st.popover("Tabular results"):
                st.dataframe(rate_of_change_df)


with st.expander("Spike test", expanded=True):
    with st.popover("Test configuration suggestions"):
        st.markdown("""
### Spike test: Input as a magnitude that’s checked across a measurement and the two adjacent measurements.  

Maybe default to same as rate of change test? 
                    """)

    spike_col_1, spike_col_2 = st.columns([1, 3])

    with spike_col_1:
        spike_suspect_threshold = st.number_input(
            "Suspect threshold",
            value=0.75 * FEET_TO_METERS,
            format="%.3f",
        )
        spike_fail_threshold = st.number_input(
            "Fail threshold",
            value=1.5 * FEET_TO_METERS,
            format="%.3f",
        )
        spike_test_toggle = st.toggle("Enable Spike test", value=True)

    with spike_col_2:
        if not spike_test_toggle:
            st.write("Spike test is disabled.")
        else:
            spike_test_config = {
                "spike_test": {
                    "suspect_threshold": spike_suspect_threshold,
                    "fail_threshold": spike_fail_threshold,
                }
            }
            spike_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        "observed": {
                            "qartod": spike_test_config,
                        }
                    }
                ),
            )

            plot = qc_helpers.plot_results(
                spike_df,
                "spike_test",
                title="Spike test",
            )
            st.bokeh_chart(plot, use_container_width=True)
            with st.popover("Tabular results"):
                st.dataframe(spike_df)


with st.expander("Flat line test", expanded=True):
    with st.popover("Test configuration suggestions"):
        st.markdown("""
### Flat line test: If there’s some lack of variance over some amount of time, mark as suspect/fail 

Suspect/Fail = how long do subsequent values stay within that threshold before it’s considered flat? (input as a time) 

For example, if all measurements over the past 4 hours are within 10 cm of each other, fail the flatline test (then tolerance = 10 cm, and time = 4 hours) 

When a sensor flatlines, the system voltage and temperature sensor may still be causing variation 

Let’s start with 0.1 feet over 2 hours for suspect, and 0.1 feet over 3 hours for fail.  


Rationale: During neap tides in Portland, you could see as little as +/- 0.25 ft per hour of variation in the 2 hours around slack tide (HW or LW)  
                    """)

    flat_line_col_1, flat_line_col_2 = st.columns([1, 3])

    with flat_line_col_1:
        flat_line_tolerance = st.number_input(
            "Tolerance (meters)",
            value=0.1 * FEET_TO_METERS,
            format="%.3f",
            help="How little change is considered flat?",
        )
        flat_line_suspect_threshold = st.number_input(
            "Suspect threshold (seconds)",
            value=2 * 60 * 60,
        )
        flat_line_fail_threshold = st.number_input(
            "Fail threshold (seconds)",
            value=3 * 60 * 60,
        )
        flat_line_test_toggle = st.toggle("Enable Flat line test", value=True)
    with flat_line_col_2:
        if not flat_line_test_toggle:
            st.write("Flat line test is disabled.")
        else:
            flat_line_test_config = {
                "flat_line_test": {
                    "tolerance": flat_line_tolerance,
                    "suspect_threshold": flat_line_suspect_threshold,
                    "fail_threshold": flat_line_fail_threshold,
                }
            }
            flat_line_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        "observed": {
                            "qartod": flat_line_test_config,
                        }
                    }
                ),
            )
            plot = qc_helpers.plot_results(
                flat_line_df,
                "flat_line_test",
                title="Flat line test",
            )
            st.bokeh_chart(plot, use_container_width=True)
            with st.popover("Tabular results"):
                st.dataframe(flat_line_df)


with st.expander("Aggregated results", expanded=True):
    qartod = {}

    if gross_range_test_toggle:
        qartod = {
            **qartod,
            **gross_range_test_config,
        }
    if rate_of_change_test_toggle:
        qartod = {
            **qartod,
            **rate_of_change_test_config,
        }
    if spike_test_toggle:
        qartod = {
            **qartod,
            **spike_test_config,
        }
    if flat_line_test_toggle:
        qartod = {
            **qartod,
            **flat_line_test_config,
        }

    all_df = qc_helpers.run_qc(
        data,
        qc_helpers.Config(
            {
                "observed": {
                    "qartod": qartod,
                }
            }
        ),
    )
    plot = qc_helpers.plot_aggregate(
        all_df,
    )
    st.bokeh_chart(plot, use_container_width=True)

    with st.popover("Tabular results and raw test config"):
        st.write(qartod)
        st.dataframe(all_df)
with st.expander("Configuration", expanded=True):
    st.markdown("### NERACOOS Sea-Eagle config")

    datum_col, calc_dates_col = st.columns([1, 1])

    with datum_col:
        st.markdown("Additional datums")

        datums = {
            "mhhw": mhhw,
            "mllw": mllw,
        }

        if mhw := st.number_input("Mean High Water (m)"):
            datums["mhw"] = mhw
        if mtl := st.number_input("Mean Tide Level (m)"):
            datums["mtl"] = mtl
        if msl := st.number_input("Mean Sea Level (m)"):
            datums["msl"] = msl
        if mlw := st.number_input("Mean Low Water (m)"):
            datums["mlw"] = mlw

    with calc_dates_col:
        st.markdown(
            "If datums were calculated, provide the date of calculation, and range that they were calculated over"
        )
        if st.toggle("Datums manually calculated or updated", value=False):
            if calc_date := st.date_input("Calculation date"):
                datums["date_calculated"] = calc_date.isoformat()
            if start_date := st.date_input("Start date"):
                datums["calculation_start_date"] = start_date.isoformat()
            if end_date := st.date_input("End date"):
                datums["calculation_end_date"] = end_date.isoformat()

    config = {
        # "title": station_info.location,
        "station_id": station_id,
        "start_dt": station_info.installation_date.isoformat(),
        "latitude": station_info.latitude,
        "longitude": station_info.longitude,
        "datums": {"manual_datums": datums},
        "qc": {"qartod": {"contexts": [{"streams": {"observed": {"qartod": qartod}}}]}},
    }
    if summary := st.text_area("Station summary information"):
        config["summary"] = summary

    st.markdown("Station configuration to provide to ODP")

    try:
        import yaml
        config_yaml = yaml.dump(config)
        st.download_button(
            "Download station config", config_yaml, file_name=f"{station_id}.yaml"
        )
        st.code(config_yaml, language="yaml")
    except ImportError:
        st.warning("Unable to install yaml for some reason, trying to just return json")
        import json
        config_json = json.dumps(config)
        st.download_button(
            "Download station config", config_json, file_name=f"{station_id}.json"
        )
        st.code(config_json, language="json")
