"""Benchmark des 4 protocoles (REST / SOAP / GraphQL / gRPC).

Mesure, pour chaque opération CRUD, chaque taille de payload (1/10/100 Ko) et
chaque niveau de concurrence (10/100/500/1000 requêtes) :
  - latence moyenne (ms)
  - latence p95 (ms)
  - débit (req/s)
  - taux d'erreur (%)

La concurrence est simulée avec des threads (chaque thread exécute des appels
séquentiels). Les métriques CPU/mémoire sont collectées par process pendant
l'exécution via psutil et consignées dans bench/metadata.json.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import psutil

from clients import make_client

OPERATIONS = ("create", "read", "update", "delete")
SIZES_KB = (1, 10, 100)
CONCURRENCIES = (10, 100, 500, 1000)

SERVERS = {
    "rest": ("http://127.0.0.1:5001", None),
    "soap": ("http://127.0.0.1:5002", None),
    "graphql": ("http://127.0.0.1:5003", None),
    "grpc": ("http://127.0.0.1:5004", "127.0.0.1:5004"),
}


def find_server_pid(protocol: str):
    """Cherche le PID du serveur à partir de la ligne de commande."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = " ".join(proc.info["cmdline"] or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if f"{protocol}" in cmd and "server.py" in cmd:
            return proc.info["pid"]
    return None


def measure_cpu_mem(pids: list, interval: float):
    """Échantillonne CPU% et RSS pendant `interval` secondes (monitoring actif)."""
    procs = []
    for pid in pids:
        try:
            procs.append(psutil.Process(pid))
        except psutil.NoSuchProcess:
            continue
    if not procs:
        return {"cpu_percent": 0.0, "rss_mb": 0.0}

    # Initialise les compteurs de psutil
    for p in procs:
        try:
            p.cpu_percent(interval=None)
        except psutil.NoSuchProcess:
            pass

    cpu_samples = []
    rss_samples = []
    end = time.perf_counter() + interval
    while time.perf_counter() < end:
        time.sleep(0.05)
        for p in procs:
            try:
                cpu_samples.append(p.cpu_percent(interval=None))
            except psutil.NoSuchProcess:
                pass
        for p in procs:
            try:
                rss_samples.append(p.memory_info().rss / (1024 * 1024))
            except psutil.NoSuchProcess:
                pass

    return {
        "cpu_percent": round(sum(cpu_samples) / len(cpu_samples), 2) if cpu_samples else 0.0,
        "rss_mb": round(sum(rss_samples) / len(rss_samples), 2) if rss_samples else 0.0,
    }


class CpuMonitor:
    """Mesure le CPU/mémoire du serveur pendant la charge.

    Le CPU est calculé à partir de la différence de cpu_times (user + system)
    entre le début et la fin de la charge, divisée par la durée réelle : c'est
    le pourcentage CPU moyen consommé par le process pendant l'exécution,
    indépendant de la fréquence d'échantillonnage (précis même pour les charges
    courtes).
    """

    def __init__(self, pids: list):
        self.pids = pids
        self.procs = []
        self._start_times = {}
        self._rss_samples = []

    def start(self):
        for pid in self.pids:
            try:
                p = psutil.Process(pid)
                self.procs.append(p)
                self._start_times[p.pid] = p.cpu_times()
            except psutil.NoSuchProcess:
                continue
        return self

    def snapshot(self) -> dict:
        total_cpu_seconds = 0.0
        rss_sum = 0.0
        n = 0
        for p in self.procs:
            try:
                end_times = p.cpu_times()
                start_times = self._start_times.get(p.pid)
                if start_times:
                    delta_user = end_times.user - start_times.user
                    delta_sys = end_times.system - start_times.system
                    total_cpu_seconds += delta_user + delta_sys
                self._rss_samples.append(p.memory_info().rss / (1024 * 1024))
                rss_sum += self._rss_samples[-1]
                n += 1
            except psutil.NoSuchProcess:
                continue
        return {
            "cpu_seconds": total_cpu_seconds,
            "rss_mb": round(rss_sum / n, 2) if n else 0.0,
        }


def run_case(client, op: str, size_kb: int, concurrency: int, monitor: CpuMonitor | None = None) -> dict:
    """Exécute `concurrency` requêtes de l'opération `op` avec un pool borné.

    `concurrency` est le nombre total de requêtes émises. Un pool de workers
    (50 au maximum) exécute ces requêtes en réutilisant les connexions
    persistantes de la session HTTP — c'est exactement le comportement d'un
    outil de charge réel (locust/k6) et cela évite l'épuisement des ports
    éphémères Windows (TIME_WAIT) qui survient avec des milliers de sockets
    courtes ouvertes simultanément.
    """
    latencies = []
    errors = 0
    lock = threading.Lock()
    max_workers = min(concurrency, 50)

    def worker(idx: int):
        nonlocal errors
        op_fn = getattr(client, op)
        start = time.perf_counter()
        try:
            op_fn(size_kb, idx)
            latency = (time.perf_counter() - start) * 1000.0
            with lock:
                latencies.append(latency)
        except Exception:
            with lock:
                errors += 1

    total = concurrency
    start_wall = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(worker, range(total)))
    wall = time.perf_counter() - start_wall

    cpu_percent = 0.0
    rss_mb = 0.0
    if monitor:
        snap = monitor.snapshot()
        if wall > 0:
            cpu_percent = round((snap["cpu_seconds"] / wall) * 100.0, 2)
        rss_mb = snap["rss_mb"]

    if not latencies:
        avg = p95 = 0.0
    else:
        latencies.sort()
        avg = statistics.mean(latencies)
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
    throughput = total / wall if wall > 0 else 0.0
    error_rate = errors / total * 100.0
    return {
        "op": op,
        "size_kb": size_kb,
        "concurrency": concurrency,
        "latency_ms_avg": round(avg, 3),
        "latency_ms_p95": round(p95, 3),
        "throughput_req_s": round(throughput, 2),
        "error_rate_pct": round(error_rate, 3),
        "wall_seconds": round(wall, 3),
        "requests": total,
        "cpu_percent": cpu_percent,
        "rss_mb": rss_mb,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True, choices=list(SERVERS))
    parser.add_argument("--out", default="results.json")
    parser.add_argument("--ops", nargs="*", default=list(OPERATIONS))
    parser.add_argument("--sizes", nargs="*", type=int, default=list(SIZES_KB))
    parser.add_argument("--concurrencies", nargs="*", type=int, default=list(CONCURRENCIES))
    args = parser.parse_args()

    target, grpc_target = SERVERS[args.protocol]
    client = make_client(args.protocol, grpc_target or target)

    pid = find_server_pid(args.protocol)
    pids = [pid] if pid else []

    results = []
    for size_kb in args.sizes:
        for concurrency in args.concurrencies:
            for op in args.ops:
                # Re-seed avant chaque run delete : chaque niveau de
                # concurrence consomme ses propres réservations jetables.
                if op == "delete" and hasattr(client, "setup"):
                    client.setup(concurrency, size_kb)
                monitor = CpuMonitor(pids).start()
                case = run_case(client, op, size_kb, concurrency, monitor)
                results.append(case)
                print(
                    f"[{client.name}] {op:6s} size={size_kb:3d}KB conc={concurrency:4d} "
                    f"avg={case['latency_ms_avg']:9.3f}ms p95={case['latency_ms_p95']:9.3f}ms "
                    f"tput={case['throughput_req_s']:8.2f}req/s err={case['error_rate_pct']:6.2f}% "
                    f"cpu={case['cpu_percent']:5.1f}% rss={case['rss_mb']:7.1f}MB",
                    flush=True,
                )

    out_path = os.path.join(os.path.dirname(__file__), args.out)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nRésultats écrits dans {out_path}", flush=True)


if __name__ == "__main__":
    main()
