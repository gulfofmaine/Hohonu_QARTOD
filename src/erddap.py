from datetime import datetime, date, timedelta, time

import erddapy
import pandas as pd

def load_erddap_data_and_config():
    import streamlit as st

    config = {}

    with st.sidebar:
        server_url = st.text_input("ERDDAP URL", "https://data.neracoos.org/erddap")
        dataset_id = st.text_input("Dataset ID")

    if not dataset_id:
        st.warning("Please enter a dataset ID")
        st.stop()

    with st.sidebar:
        with st.expander("Data selector", expanded=True):
            now = datetime.now()
            week_ago = now - timedelta(days=7)

            date_range = st.date_input(
                "Date range",
                (week_ago, now),
                max_value=now,
                help="""
                    Date range to load testing data for.
                    """
            )

            load_data_button = st.toggle("Load data")

    if not load_data_button:
        st.warning("Please select a date range and toggle 'Load data' to start generating QARTOD config")
        st.stop()

    @st.cache_data
    def fetch_data(server_url, dataset_id, date_range):

        e = erddapy.ERDDAP(server=server_url, protocol="tabledap", response="csv")
        e.dataset_id = dataset_id
        e.constraints = {"time>=": date_range[0].isoformat(), "time<=": date_range[1].isoformat()}

        df = e.to_pandas(parse_dates=True)

        return df

    df = fetch_data(server_url, dataset_id, date_range)

    with st.sidebar:
        with st.expander("Rename columns", expanded=False):
            st.markdown("""
                Rename columns
                - Usually units need to be removed from column names
                - Existing QARTOD test columns should be renamed
                        """)
            rename_columns = st.data_editor(
                pd.DataFrame({"source_column": ["time (UTC)", "navd88_meters (m)"],  "target_column": ["time", "navd88_meters"]}),
                num_rows="dynamic"
            )
            rename_map = {row["source_column"]: row["target_column"] for _, row in rename_columns.iterrows()}
            df = df.rename(columns=rename_map)
        
        df["time"] = pd.to_datetime(df["time"])

        column = st.selectbox("Select a column to compute QARTOD for", df.columns)


    return df, config, column