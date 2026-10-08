from app.api import app

c = app.test_client()


def test_health():
    assert c.get("/health").status_code == 200


def test_nearby_missing_params():
    assert c.get("/nearby").status_code == 400


def test_nearby_bad_latitude():
    assert c.get("/nearby?lat=95&lon=-73.9&radius=500").status_code == 400


def test_within_requires_polygon():
    assert c.post("/within", json={"type": "Point", "coordinates": [0, 0]}).status_code == 400


def test_unknown_spark_collection():
    assert c.get("/spark/xyz").status_code == 404
