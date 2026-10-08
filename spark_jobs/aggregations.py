"""Spark lee 'trips' desde MongoDB y escribe agregaciones espaciales/temporales en colecciones nuevas."""
import os, time
from pyspark.sql import SparkSession, functions as F

URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")
DB = "taxi"
CELL = 0.01   # grados (~1 km): tamaño de la celda de la grilla

spark = (SparkSession.builder.appName("taxi-aggregations")
         .config("spark.mongodb.read.connection.uri", URI)
         .config("spark.mongodb.write.connection.uri", URI)
         .getOrCreate())


def save(df, name):
    df.write.format("mongodb").mode("overwrite").option("database", DB).option("collection", name).save()
    print(f"-> colección '{name}' guardada")


t0 = time.time()
trips = (spark.read.format("mongodb").option("database", DB).option("collection", "trips").load()
         .select(F.col("location.coordinates").getItem(0).alias("lon"),
                 F.col("location.coordinates").getItem(1).alias("lat"),
                 "pickup_datetime", "trip_duration"))

# 1) Conteo por celda de grilla
grid = (trips
        .withColumn("cell_x", F.floor(F.col("lon") / CELL))
        .withColumn("cell_y", F.floor(F.col("lat") / CELL))
        .groupBy("cell_x", "cell_y")
        .agg(F.count("*").alias("trips"), F.round(F.avg("trip_duration"), 1).alias("avg_duration"))
        .withColumn("center_lon", (F.col("cell_x") + 0.5) * CELL)
        .withColumn("center_lat", (F.col("cell_y") + 0.5) * CELL)
        .withColumn("center", F.struct(F.lit("Point").alias("type"),
                                       F.array("center_lon", "center_lat").alias("coordinates")))
        .cache())
save(grid, "grid_counts")

# 2) Zonas de alta concentración: celdas en el percentil 95 de viajes
threshold = grid.approxQuantile("trips", [0.95], 0.01)[0]
save(grid.filter(F.col("trips") >= threshold), "hot_zones")
print(f"umbral zona caliente (p95): {threshold}")

# 3) Comportamiento temporal
agg = [F.count("*").alias("trips"), F.round(F.avg("trip_duration"), 1).alias("avg_duration")]
save(trips.groupBy(F.hour("pickup_datetime").alias("hour")).agg(*agg), "hourly")
save(trips.groupBy(F.dayofweek("pickup_datetime").alias("dow"),
                   F.date_format("pickup_datetime", "EEEE").alias("day_name")).agg(*agg), "weekday")
save(trips.groupBy(F.month("pickup_datetime").alias("month")).agg(*agg), "monthly")

print(f"tiempo total: {time.time() - t0:.1f}s")
spark.stop()
