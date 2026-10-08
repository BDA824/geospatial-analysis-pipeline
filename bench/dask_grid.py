"""Benchmark Dask: agregación por grilla leyendo directo del CSV."""
import json, os, statistics, time
import dask.dataframe as dd
import numpy as np
import pandas as pd
from dask.distributed import Client
from ingest.clean import clean_df

CSV, CELL, REPS = "/data/train.csv", 0.01, 3


def prep(df):
    df = clean_df(df)
    return pd.DataFrame({"cx": np.floor(df.pickup_longitude / CELL).astype("int64"),
                         "cy": np.floor(df.pickup_latitude / CELL).astype("int64"),
                         "trip_duration": df.trip_duration})


if __name__ == "__main__":
    client = Client(os.environ.get("DASK_SCHEDULER", "tcp://dask-scheduler:8786"))
    client.wait_for_workers(int(os.environ.get("N_WORKERS", 1)))
    meta = pd.DataFrame({"cx": pd.Series(dtype="int64"), "cy": pd.Series(dtype="int64"),
                         "trip_duration": pd.Series(dtype="float64")})
    times = []
    for _ in range(REPS):
        t0 = time.time()
        ddf = dd.read_csv(CSV, blocksize="16MB", assume_missing=True,
                          parse_dates=["pickup_datetime", "dropoff_datetime"])
        ddf.map_partitions(prep, meta=meta).groupby(["cx", "cy"]).trip_duration.agg(["count", "mean"]).compute()
        times.append(time.time() - t0)
    print("RESULT " + json.dumps({"engine": "dask", "seconds": times, "median": statistics.median(times)}))
