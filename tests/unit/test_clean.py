import pandas as pd
from etl_process.transform import clean_df, to_docs

BASE = dict(id="id1", vendor_id=1, pickup_datetime="2016-03-14 17:24:55", passenger_count=1,
            pickup_longitude=-73.98, pickup_latitude=40.76, dropoff_longitude=-73.96,
            dropoff_latitude=40.77, trip_duration=455)


def frame(**overrides):
    return pd.DataFrame([{**BASE, **overrides}])


def test_valid_row_is_kept():
    assert len(clean_df(frame())) == 1


def test_null_coordinate_dropped():
    assert len(clean_df(frame(pickup_latitude=None))) == 0


def test_out_of_range_coordinate_dropped():
    assert len(clean_df(frame(pickup_longitude=0.0))) == 0


def test_absurd_duration_dropped():
    assert len(clean_df(frame(trip_duration=3526282))) == 0


def test_geojson_point_is_lon_lat():
    doc = to_docs(clean_df(frame()))[0]
    assert doc["location"] == {"type": "Point", "coordinates": [-73.98, 40.76]}
