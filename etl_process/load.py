"""Ingesta con Dask: lee el CSV por particiones, limpia y carga en MongoDB por lotes."""
import os, time
import dask.dataframe as dd
import pandas as pd
from dask.distributed import Client
from pymongo import MongoClient, GEOSPHERE
from ingest.clean import clean_df, to_docs

CSV = "/data/train.csv"
DB, COLL = "taxi", "trips"
BATCH = 5000
URI = os.environ.get("MONGO_URI", "mongodb://mongo:27017")


def process_partition(df, uri):
    """Corre en un worker de Dask, una vez por partición."""
    raw = len(df)
    docs = to_docs(clean_df(df))
    client = MongoClient(uri)
    col = client[DB][COLL]
    inserted = 0
    for i in range(0, len(docs), BATCH):
        inserted += len(col.insert_many(docs[i:i + BATCH], ordered=False).inserted_ids)
    client.close()
    return pd.DataFrame({"raw": [raw], "kept": [len(docs)], "inserted": [inserted]})


if __name__ == "__main__":
    t0 = time.time()
    client = Client(os.environ.get("DASK_SCHEDULER", "tcp://dask-scheduler:8786"))
    client.wait_for_workers(2)

    mongo = MongoClient(URI)
    mongo[DB][COLL].drop()          # ingesta repetible

    ddf = dd.read_csv(CSV, blocksize="16MB", assume_missing=True,
                      parse_dates=["pickup_datetime", "dropoff_datetime"])
    meta = pd.DataFrame({k: pd.Series(dtype="int64") for k in ["raw", "kept", "inserted"]})
    res = ddf.map_partitions(process_partition, URI, meta=meta).compute()

    mongo[DB][COLL].create_index([("location", GEOSPHERE)])
    raw, kept = int(res.raw.sum()), int(res.kept.sum())
    print(f"particiones: {len(res)} | leídos: {raw} | cargados: {kept} | "
          f"descartados: {raw - kept} ({100 * (raw - kept) / raw:.2f}%)")
    print(f"docs en Mongo: {mongo[DB][COLL].count_documents({})} | tiempo: {time.time() - t0:.1f}s")
