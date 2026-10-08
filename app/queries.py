"""Consultas geoespaciales. Todas reciben parámetros (nada fijo en el código)."""

PROJECTION = {"vendor_id": 1, "passenger_count": 1, "pickup_datetime": 1,
              "trip_duration": 1, "location": 1}


def _point(lat, lon):
    return {"type": "Point", "coordinates": [lon, lat]}   # GeoJSON: [lon, lat]


def nearby(col, lat, lon, radius_m, limit=100):
    """$near: ordenado del más cercano al más lejano, dentro de radius_m metros."""
    q = {"location": {"$near": {"$geometry": _point(lat, lon), "$maxDistance": radius_m}}}
    return list(col.find(q, PROJECTION).limit(limit))


def within_polygon(col, polygon, limit=100):
    """$geoWithin: registros dentro de un polígono GeoJSON."""
    q = {"location": {"$geoWithin": {"$geometry": polygon}}}
    return list(col.find(q, PROJECTION).limit(limit))


def geonear_by_hour(col, lat, lon, radius_m):
    """$geoNear (agregación): viajes cerca de un punto, agrupados por hora, con distancia media."""
    pipeline = [
        {"$geoNear": {"near": _point(lat, lon), "distanceField": "dist_m",
                      "maxDistance": radius_m, "spherical": True}},
        {"$group": {"_id": {"$hour": "$pickup_datetime"},
                    "trips": {"$sum": 1},
                    "avg_duration": {"$avg": "$trip_duration"},
                    "avg_dist_m": {"$avg": "$dist_m"}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "hour": "$_id", "trips": 1, "avg_duration": 1, "avg_dist_m": 1}},
    ]
    return list(col.aggregate(pipeline))
