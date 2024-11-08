import streamlit as st

from regions import GulfOfMaine
import qc_helpers

FEET_TO_METERS = 0.3048


region = GulfOfMaine()

st.markdown("""
# Water level QARTOD and config generation

This tool is to help generate QARTOD configuration files
for Hohonu, Brown/URI, and other water level gauges deployed for NERACOOS. 
""")

st.markdown(region.general_info)

HOHONU_DATA_SOURCE = "Hohonu"
BROWN_DATA_SOURCE = "Brown/URI"
ERDDAP = "ERDDAP"
DATA_SOURCES = [HOHONU_DATA_SOURCE, BROWN_DATA_SOURCE, ERDDAP]

with st.sidebar:
    data_source = st.selectbox("Select data source", DATA_SOURCES)


qartod = {}
column = "navd88_meters"
if data_source == HOHONU_DATA_SOURCE:
    from hohonu_api import load_hohonu_streamlit_data_and_config

    data, config = load_hohonu_streamlit_data_and_config()

elif data_source == BROWN_DATA_SOURCE:
    from things_api import load_things_streamlit_data_and_config

    data, config = load_things_streamlit_data_and_config()


elif data_source == ERDDAP:
    from erddap import load_erddap_data_and_config

    data, config, column = load_erddap_data_and_config()
else:
    st.error("No idea how you selected another data source, exploding now")
    st.stop()

with st.expander("Loaded data"):
    st.dataframe(data)
    st.line_chart(data, x="time", y=column, y_label=column)

with st.sidebar:
    with st.expander("Datum selector", expanded=True):
        st.markdown("""
                    
    Datums should be entered as meters in from NAVD88.

    They can either be entered from known values,
    or can be calculated using [CO-OPS Tidal Analysis Datum Calculator](https://access.co-ops.nos.noaa.gov/datumcalc/).
                    
    For calculation, at least a month's worth of clean data is required.
    """)

        mhhw = st.number_input(
            "Mean High High Water (MHHW meters)",
            # value=station_info.mhhw,
            help="""
            The mean high high water (MHHW) datum offset for the gauge in meters from navd88_meters.datum for the gauge.
            """,
        )

        mllw = st.number_input(
            "Mean Low Low Water (MLLW meters)",
            # value=station_info.mllw,
            help="""
            The mean low low water (MLLW) datum offset for the gauge in meters from navd88_meters.
            """,
        )


test_defaults = region.calculate_defaults(mllw, mhhw)

with st.expander("Gross range test", expanded=True):
    with st.popover("Test configuration suggestions"):
        st.markdown(region.gross_range_test_help)

    gross_col_1, gross_col_2 = st.columns([1, 3])

    with gross_col_1:
        st.markdown("##### Suspect span")

        gross_suspect_upper_limit = st.number_input(
            "Upper limit",
            value=test_defaults.gross_range.suspect_upper_limit,
            key="gross_suspect_upper_limit",
            help="""
            The upper limit of the gross range test.
            """,
        )

        gross_suspect_lower_limit = st.number_input(
            "Lower limit",
            value=test_defaults.gross_range.suspect_lower_limit,
            key="gross_suspect_lower_limit",
            help="""
            The lower limit of the gross range test.
            """,
        )

        st.markdown("##### Fail span")

        gross_fail_upper_limit = st.number_input(
            "Upper limit",
            value=test_defaults.gross_range.fail_upper_limit,
            key="gross_fail_upper_limit",
            help="""
            The upper limit of the gross range test.
            """,
        )

        gross_fail_lower_limit = st.number_input(
            "Lower limit",
            value=test_defaults.gross_range.fail_lower_limit,
            key="gross_fail_lower_limit",
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
                    "suspect_span": [gross_suspect_lower_limit, gross_suspect_upper_limit],
                    "fail_span": [gross_fail_lower_limit, gross_fail_upper_limit],
                }
            }
            qartod.update(gross_range_test_config)

            gross_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        column: {
                            "qartod": gross_range_test_config,
                        }
                    }
                ),
            )

            plot = qc_helpers.plot_results(
                gross_df,
                "gross_range_test",
                title="Gross range test",
                var_name=column,
            )
            st.bokeh_chart(plot, use_container_width=True)

            with st.popover("Tabular results"):
                st.dataframe(gross_df)

with st.expander("Rate of change test", expanded=True):
    with st.popover("Test configuration suggestions"):
        st.markdown(region.rate_of_change_test_help)

    rate_col_1, rate_col_2 = st.columns([1, 3])

    with rate_col_1:
        rate_threshold = st.number_input(
            "Rate threshold",
            value=test_defaults.rate_of_change.rate_threshold,
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
            qartod.update(rate_of_change_test_config)

            rate_of_change_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        column: {
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
        st.markdown(region.spike_test_help)

    spike_col_1, spike_col_2 = st.columns([1, 3])

    with spike_col_1:
        spike_suspect_threshold = st.number_input(
            "Suspect threshold",
            value=test_defaults.spike.suspect_threshold,
            format="%.3f",
        )
        spike_fail_threshold = st.number_input(
            "Fail threshold",
            value=test_defaults.spike.fail_threshold,
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
            qartod.update(spike_test_config)

            spike_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        column: {
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
        st.markdown(region.flat_line_test_help)

    flat_line_col_1, flat_line_col_2 = st.columns([1, 3])

    with flat_line_col_1:
        flat_line_tolerance = st.number_input(
            "Tolerance (meters)",
            value=test_defaults.flat_line.tolerance,
            format="%.3f",
            help="How little change is considered flat?",
        )
        flat_line_suspect_threshold = st.number_input(
            "Suspect threshold (seconds)",
            value=test_defaults.flat_line.suspect_threshold,
        )
        flat_line_fail_threshold = st.number_input(
            "Fail threshold (seconds)",
            value=test_defaults.flat_line.fail_threshold,
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
            qartod.update(flat_line_test_config)

            flat_line_df = qc_helpers.run_qc(
                data,
                qc_helpers.Config(
                    {
                        column: {
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
    all_df = qc_helpers.run_qc(
        data,
        qc_helpers.Config(
            {
                column: {
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

    config.update({
        "datums": {"manual_datums": datums},
        "qc": {"qartod": {"contexts": [{"streams": {column: {"qartod": qartod}}}]}},
    })

    if title := st.text_input("Station title", help="For display in ERDDAP, Mariners, and other locations, such as 'Department of Marine Resources, Boothbay Harbor, ME Hohonu tide gauge'"):
        config["title"] = title

    if summary := st.text_area(
            "Station summary information", 
            help="""
            What should we and our users know about a station?

            - Why is is sited here?
            - Are there any site specific features to be aware of (dries out at low tide, ice risk in winter,...)?
            """
        ):
        config["summary"] = summary

    st.markdown("Station configuration to provide to ODP")

    try:
        import yaml
        config_yaml = yaml.dump(config)
        st.download_button(
            "Download station config", config_yaml, file_name="config.yaml"
        )
        st.code(config_yaml, language="yaml")
    except ImportError:
        st.warning("Unable to install yaml for some reason, trying to just return json")
        import json
        config_json = json.dumps(config)
        st.download_button(
            "Download station config", config_json, file_name="config.json"
        )
        st.code(config_json, language="json")
