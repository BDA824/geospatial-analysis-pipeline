"""Prueba básica contra la API real + Mongo del stack de CI. Se ejecuta DENTRO del contenedor api."""
import json, os, sys, time, urllib.request
from datetime import datetime
from pymongo import GEOSPHERE, MongoClient

BASE = "http://localhost:5000"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return json.load(r)


for _ in range(30):                       # esperar a que gunicorn arranque
    try:
        get("/health"); break
    except Exception:
        time.sleep(1)
else:
    sys.exit("la API no respondió")

col = MongoClient(os.environ["MONGO_URI"])[os.environ.get("DB_NAME", "taxi")].trips
col.drop()
pt = lambda lon, lat: {"type": "Point", "coordinates": [lon, lat]}
col.insert_many([
    {"_id": "a", "trip_duration": 300, "pickup_datetime": datetime(2016, 3, 1, 8), "location": pt(-73.9855, 40.7580)},
    {"_id": "b", "trip_duration": 900, "pickup_datetime": datetime(2016, 3, 1, 9), "location": pt(-73.80, 40.65)},
])
col.create_index([("location", GEOSPHERE)])

assert get("/nearby?lat=40.758&lon=-73.9855&radius=500")["count"] == 1, "nearby"
assert get("/geonear?lat=40.758&lon=-73.9855&radius=500")["results"][0]["trips"] == 1, "geonear"

poly = {"type": "Polygon", "coordinates": [[[-74.0, 40.75], [-73.97, 40.75], [-73.97, 40.77], [-74.0, 40.77], [-74.0, 40.75]]]}
req = urllib.request.Request(BASE + "/within", json.dumps(poly).encode(), {"Content-Type": "application/json"})
assert json.load(urllib.request.urlopen(req))["count"] == 1, "within"
print("SMOKE OK")
