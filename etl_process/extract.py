import glob, os, sys, zipfile

DATA = "/data"
CSV = f"{DATA}/train.csv"

if os.path.exists(CSV):
    print("train.csv ya existe, nada que descargar")
    sys.exit(0)

if not glob.glob(f"{DATA}/*.zip"):
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    api.competition_download_file("nyc-taxi-trip-duration", "train.zip", path=DATA)

for z in glob.glob(f"{DATA}/*.zip"):
    with zipfile.ZipFile(z) as f:
        f.extractall(DATA)
print("listo:", os.listdir(DATA))