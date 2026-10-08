import pandas as pd

# Caja aproximada de Nueva York (lon, lat)
LON_MIN, LON_MAX = -74.3, -73.7
LAT_MIN, LAT_MAX = 40.5, 40.95
DUR_MIN, DUR_MAX = 10, 86400   # segundos: 10 s a 24 h

COORDS = ["pickup_longitude", "pickup_latitude", "dropoff_longitude", "dropoff_latitude"]


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=COORDS + ["pickup_datetime", "trip_duration"]).copy()
    df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"])
    ok = (
        df.pickup_longitude.between(LON_MIN, LON_MAX)
        & df.dropoff_longitude.between(LON_MIN, LON_MAX)
        & df.pickup_latitude.between(LAT_MIN, LAT_MAX)
        & df.dropoff_latitude.between(LAT_MIN, LAT_MAX)
        & df.trip_duration.between(DUR_MIN, DUR_MAX)
        & (df.passenger_count >= 1)
    )
    return df[ok]


def point(lon, lat):
    return {"type": "Point", "coordinates": [float(lon), float(lat)]}


def to_docs(df: pd.DataFrame) -> list:
    return [
        {
            "_id": r.id,
            "vendor_id": int(r.vendor_id),
            "passenger_count": int(r.passenger_count),
            "pickup_datetime": r.pickup_datetime.to_pydatetime(),
            "trip_duration": int(r.trip_duration),
            "location": point(r.pickup_longitude, r.pickup_latitude),
            "dropoff_location": point(r.dropoff_longitude, r.dropoff_latitude),
        }
        for r in df.itertuples(index=False)
    ]