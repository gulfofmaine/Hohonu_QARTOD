import numpy as np
import pandas as pd
from ioos_qc.config import Config
from ioos_qc.stores import PandasStore
from ioos_qc.streams import PandasStream

from bokeh.layouts import gridplot  # noqa: E402
from bokeh.plotting import figure, show  # noqa: E402


def run_qc(df: pd.DataFrame, config: Config) -> pd.DataFrame:
    """Run a QARTOD config and return a dataframe with source data and test results"""
    ps = PandasStream(df)
    results = ps.run(config)
    store = PandasStore(results)
    store.compute_aggregate("qc_rollup")

    return pd.concat([df, store.save(write_data=False, write_axes=False)], axis=1)


def plot_results(
    data: pd.DataFrame,
    test_name: str,
    var_name="navd88_meters",
    title: str = None,
):
    """Plot the qc results on top of the source data"""

    time = data["time"]
    obs = data[var_name]
    qc_test_column = f"{var_name}_qartod_{test_name}"
    try:
        qc_test = data[qc_test_column]
    except KeyError as e:
        raise KeyError(
            f"{qc_test_column} is not in the dataframe. {data.columns}"
        ) from e
    
    try:
        qc_pass = np.ma.masked_where(qc_test != 1, obs)
    except IndexError as e:
        raise IndexError(
            f"{qc_test=}, {obs=}"
        ) from e
    
    qc_suspect = np.ma.masked_where(qc_test != 3, obs)
    qc_fail = np.ma.masked_where(qc_test != 4, obs)
    qc_notrun = np.ma.masked_where(qc_test != 2, obs)

    if title:
        display_title = f"{title}: {test_name}"
    else:
        display_title = test_name

    p1 = figure(x_axis_type="datetime", title=display_title)
    p1.grid.grid_line_alpha = 0.3
    p1.xaxis.axis_label = "Time"
    p1.yaxis.axis_label = "Observation Value"

    p1.line(time, obs, legend_label="obs", color="#A6CEE3")
    p1.circle(
        time,
        qc_notrun,
        size=2,
        legend_label="qc not run",
        color="gray",
        alpha=0.2,
    )
    p1.circle(time, qc_pass, size=4, legend_label="qc pass", color="green", alpha=0.5)
    p1.circle(
        time,
        qc_suspect,
        size=4,
        legend_label="qc suspect",
        color="orange",
        alpha=0.7,
    )
    p1.circle(time, qc_fail, size=6, legend_label="qc fail", color="red", alpha=1.0)

    return gridplot([[p1]], width=800, height=400)


def plot_aggregate(
    data: pd.DataFrame,
    var_name="navd88_meters",
    aggregate_name: str = "qartod_qc_rollup",
    title: str = None,
):
    """Plot the qc results on top of the source data"""

    time = data["time"]
    obs = data[var_name]
    qc_test = data[aggregate_name]

    qc_pass = np.ma.masked_where(qc_test != 1, obs)
    qc_suspect = np.ma.masked_where(qc_test != 3, obs)
    qc_fail = np.ma.masked_where(qc_test != 4, obs)
    qc_notrun = np.ma.masked_where(qc_test != 2, obs)

    display_title = aggregate_name

    p1 = figure(x_axis_type="datetime", title=display_title)
    p1.grid.grid_line_alpha = 0.3
    p1.xaxis.axis_label = "Time"
    p1.yaxis.axis_label = "Observation Value"

    p1.line(time, obs, legend_label="obs", color="#A6CEE3")
    p1.circle(
        time,
        qc_notrun,
        size=2,
        legend_label="qc not run",
        color="gray",
        alpha=0.2,
    )
    p1.circle(time, qc_pass, size=4, legend_label="qc pass", color="green", alpha=0.5)
    p1.circle(
        time,
        qc_suspect,
        size=4,
        legend_label="qc suspect",
        color="orange",
        alpha=0.7,
    )
    p1.circle(time, qc_fail, size=6, legend_label="qc fail", color="red", alpha=1.0)

    return gridplot([[p1]], width=800, height=400)
