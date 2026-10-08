"""Benchmark Spark: agregación por grilla leyendo directo del CSV (mismo trabajo que bench/dask_grid.py)."""
import json, statistics, time
from pyspark.sql import SparkSession, functions as F

CSV, CELL, REPS = "/data/train.csv", 0.01, 3
SCHEMA = ("id string, vendor_id int, pickup_datetime timestamp, dropoff_datetime timestamp, "
          "passenger_count int, pickup_longitude double, pickup_latitude double, "
          "dropoff_longitude double, dropoff_latitude double, store_and_fwd_flag string, trip_duration int")

spark = (SparkSession.builder.appName("bench-spark")
         .config("spark.sql.files.maxPartitionBytes", 16 * 1024 * 1024)   # ~ blocksize de Dask
         .getOrCreate())

times = []
for _ in range(REPS):
    t0 = time.time()
    df = spark.read.csv(CSV, header=True, schema=SCHEMA, timestampFormat="yyyy-MM-dd HH:mm:ss")
    df = df.filter(F.col("pickup_longitude").between(-74.3, -73.7) & F.col("dropoff_longitude").between(-74.3, -73.7)
                   & F.col("pickup_latitude").between(40.5, 40.95) & F.col("dropoff_latitude").between(40.5, 40.95)
                   & F.col("trip_duration").between(10, 86400) & (F.col("passenger_count") >= 1))
    res = (df.groupBy(F.floor(F.col("pickup_longitude") / CELL).alias("cx"),
                      F.floor(F.col("pickup_latitude") / CELL).alias("cy"))
             .agg(F.count("*").alias("count"), F.avg("trip_duration").alias("mean")))
    res.write.format("noop").mode("overwrite").save()   # fuerza el cómputo completo
    times.append(time.time() - t0)

print("RESULT " + json.dumps({"engine": "spark", "seconds": times, "median": statistics.median(times)}))
spark.stop()
