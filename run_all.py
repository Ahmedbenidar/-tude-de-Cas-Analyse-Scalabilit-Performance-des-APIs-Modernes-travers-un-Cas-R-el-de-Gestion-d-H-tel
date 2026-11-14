"""Orchestrateur : lance les 4 serveurs, exécute le benchmark complet, stoppe tout.

Usage:
    python run_all.py            # benchmark complet (4 protocoles, toutes tailles/conc.)
    python run_all.py --quick    # version réduite pour validation rapide
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "grpc_svc"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SERVERS = {
    "rest": ("rest/server.py", "http://127.0.0.1:5001/health", "5001"),
    "soap": ("soap/server.py", "http://127.0.0.1:5002/health", "5002"),
    "graphql": ("graphql_svc/server.py", "http://127.0.0.1:5003/health", "5003"),
    "grpc": ("grpc_svc/server.py", None, "5004"),
}


def wait_http(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                return resp.status == 200
        except Exception:
            time.sleep(0.2)
    return False


def wait_grpc_port(port: int, timeout: float = 15.0) -> bool:
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def start_server(name: str):
    script, health_url, port = SERVERS[name]
    env = dict(os.environ)
    env["PYTHONPATH"] = BASE + os.pathsep + os.path.join(BASE, "grpc_svc")
    env["PORT"] = port
    log_path = os.path.join(BASE, "bench", f"server_{name}.log")
    log_file = open(log_path, "a", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE, script)],
        env=env,
        cwd=BASE,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    if health_url:
        ready = wait_http(health_url)
    else:
        ready = wait_grpc_port(int(port))
    if not ready:
        proc.terminate()
        raise RuntimeError(f"{name} n'a pas démarré")
    return proc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="version réduite")
    args = parser.parse_args()

    if args.quick:
        sizes = [1, 100]
        concurrencies = [10, 100]
        ops = ["read", "create"]
    else:
        sizes = [1, 10, 100]
        concurrencies = [10, 100, 500, 1000]
        ops = ["create", "read", "update", "delete"]

    procs = {}
    try:
        for name in SERVERS:
            print(f"Démarrage de {name}...", flush=True)
            procs[name] = start_server(name)
            print(f"  {name} prêt", flush=True)

        all_results = {}
        for name in SERVERS:
            print(f"\n=== Benchmark {name} ===", flush=True)
            out = os.path.join(BASE, "bench", f"results_{name}.json")
            cmd = [
                sys.executable,
                os.path.join(BASE, "bench", "benchmark.py"),
                "--protocol", name,
                "--out", f"results_{name}.json",
                "--ops", *ops,
                "--sizes", *[str(s) for s in sizes],
                "--concurrencies", *[str(c) for c in concurrencies],
            ]
            env = dict(os.environ)
            env["PYTHONPATH"] = BASE + os.pathsep + os.path.join(BASE, "grpc_svc") + os.pathsep + os.path.join(BASE, "bench")
            res = subprocess.run(cmd, env=env, cwd=BASE, capture_output=True, text=True, encoding="utf-8", errors="replace")
            sys.stdout.write(res.stdout)
            sys.stderr.write(res.stderr)
            if res.returncode != 0:
                raise RuntimeError(f"benchmark {name} échoué (exit {res.returncode})")
            with open(out, encoding="utf-8") as f:
                all_results[name] = json.load(f)

        summary = os.path.join(BASE, "bench", "all_results.json")
        with open(summary, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\nRésultats consolidés: {summary}", flush=True)
    finally:
        for name, proc in procs.items():
            try:
                proc.terminate()
            except Exception:
                pass
        for name, proc in procs.items():
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()


if __name__ == "__main__":
    main()
