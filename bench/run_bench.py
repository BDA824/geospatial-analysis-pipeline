"""Uso: python3 bench/run_bench.py dask|spark N_WORKERS
Escala los workers, ejecuta el benchmark y mide el pico de memoria (docker stats) de los contenedores del motor."""
import csv, json, os, re, subprocess, sys, threading, time

engine, n = sys.argv[1], int(sys.argv[2])
UNITS = {"B": 1, "KiB": 1024, "MiB": 1024 ** 2, "GiB": 1024 ** 3}


def sh(cmd):
    return subprocess.run(cmd, shell=True, text=True, capture_output=True)


def mem_mb():
    out = sh('docker stats --no-stream --format "{{.Name}};{{.MemUsage}}"').stdout
    total = 0.0
    for line in out.splitlines():
        name, usage = line.split(";")
        m = re.match(r"([\d.]+)\s*([A-Za-z]+)", usage.split("/")[0].strip())
        if engine in name and m:
            total += float(m[1]) * UNITS[m[2]]
    return total / 1024 ** 2


if engine == "dask":
    sh(f"docker compose up -d --scale dask-worker={n} dask-scheduler dask-worker")
    cmd = f"docker compose run --rm -e N_WORKERS={n} bench python bench/dask_grid.py"
else:
    sh(f"docker compose up -d --scale spark-worker={n} spark-master spark-worker")
    cmd = "docker compose run --rm spark-submit /app/spark_jobs/bench_grid.py"
time.sleep(15)   # que los workers se registren

peak, running = [mem_mb()], True


def sampler():
    while running:
        peak.append(mem_mb())


th = threading.Thread(target=sampler)
th.start()
out = sh(cmd)
running = False
th.join()

line = [l for l in out.stdout.splitlines() if l.startswith("RESULT ")]
if not line:
    sys.exit("El benchmark falló:\n" + out.stdout[-2000:] + out.stderr[-2000:])
res = json.loads(line[-1][7:])
row = [engine, n, round(res["median"], 2), round(max(peak), 0)]
print(f"motor={row[0]} workers={row[1]} mediana_s={row[2]} pico_memoria_MB={row[3]}")
with open("bench/results.csv", "a", newline="") as f:
    csv.writer(f).writerow(row)
