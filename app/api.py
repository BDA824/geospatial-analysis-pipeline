import os
from flask import Flask, abort, jsonify, request
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError
from app import queries

app = Flask(__name__)
db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "taxi")]

# colección de Spark -> (campo de orden, sentido)
SPARK_COLLECTIONS = {
    "grid_counts": ("trips", -1),
    "hot_zones": ("trips", -1),
    "hourly": ("hour", 1),
    "weekday": ("dow", 1),
    "monthly": ("month", 1),
}


@app.errorhandler(ValueError)
def bad_request(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(OperationFailure)
def invalid_query(e):
    return jsonify(error=f"consulta inválida: {e}"), 400


@app.errorhandler(PyMongoError)
def db_down(e):
    return jsonify(error="base de datos no disponible"), 503


def num(name, lo, hi, default=None):
    raw = request.args.get(name, default)
    if raw is None:
        raise ValueError(f"falta el parámetro '{name}'")
    try:
        v = float(raw)
    except ValueError:
        raise ValueError(f"'{name}' debe ser numérico")
    if not lo <= v <= hi:
        raise ValueError(f"'{name}' debe estar entre {lo} y {hi}")
    return v


def point_args():
    return num("lat", -90, 90), num("lon", -180, 180), num("radius", 1, 20000)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/nearby")
def nearby():
    lat, lon, radius = point_args()
    limit = int(num("limit", 1, 1000, 100))
    docs = queries.nearby(db.trips, lat, lon, radius, limit)
    return jsonify(count=len(docs), results=docs)


@app.post("/within")
def within():
    body = request.get_json(silent=True) or {}
    polygon = body.get("geometry", body) if body.get("type") == "Feature" else body
    if polygon.get("type") != "Polygon" or not polygon.get("coordinates"):
        raise ValueError("el cuerpo debe ser un GeoJSON de tipo Polygon (o Feature con Polygon)")
    limit = int(num("limit", 1, 1000, 100))
    docs = queries.within_polygon(db.trips, polygon, limit)
    return jsonify(count=len(docs), results=docs)


@app.get("/geonear")
def geonear():
    lat, lon, radius = point_args()
    return jsonify(results=queries.geonear_by_hour(db.trips, lat, lon, radius))


@app.get("/spark/<name>")
def spark_results(name):
    if name not in SPARK_COLLECTIONS:
        abort(404, description=f"colecciones válidas: {list(SPARK_COLLECTIONS)}")
    field, sense = SPARK_COLLECTIONS[name]
    limit = int(num("limit", 1, 5000, 100))
    docs = list(db[name].find({}, {"_id": 0}).sort(field, sense).limit(limit))
    return jsonify(count=len(docs), results=docs)
