"""Génère les graphiques de comparaison à partir de bench/all_results.json.

Produit des PNG dans docs/ :
  - 01-chart-latence-100kb.png   (latence moyenne à 100 Ko, par concurrency)
  - 02-chart-throughput-1kb.png  (débit à 1 Ko, par concurrency)
  - 03-chart-cpu-100kb.png       (CPU% moyen à 100 Ko, par concurrency)
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
os.makedirs(DOCS, exist_ok=True)

COLORS = {
    "rest": "#e76f51",
    "soap": "#e9c46a",
    "graphql": "#2a9d8f",
    "grpc": "#264653",
}
LABELS = {"rest": "REST", "soap": "SOAP", "graphql": "GraphQL", "grpc": "gRPC"}
CONCURRENCIES = [10, 100, 500, 1000]


def load():
    with open(os.path.join(BASE, "bench", "all_results.json"), encoding="utf-8") as f:
        return json.load(f)


def chart_latency(data):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for proto in ("rest", "soap", "graphql", "grpc"):
        ys = []
        for conc in CONCURRENCIES:
            reads = [
                c for c in data[proto]
                if c["op"] == "read" and c["size_kb"] == 100 and c["concurrency"] == conc
            ]
            ys.append(reads[0]["latency_ms_avg"])
        ax.plot(CONCURRENCIES, ys, marker="o", linewidth=2.2,
                color=COLORS[proto], label=LABELS[proto])
    ax.set_xlabel("Concurrence (nombre de requêtes)")
    ax.set_ylabel("Latence moyenne (ms)")
    ax.set_title("Latence de lecture (GET) — payload 100 Ko")
    ax.set_xticks(CONCURRENCIES)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, "01-chart-latence-100kb.png"), dpi=130)
    plt.close(fig)


def chart_throughput(data):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for proto in ("rest", "soap", "graphql", "grpc"):
        ys = []
        for conc in CONCURRENCIES:
            reads = [
                c for c in data[proto]
                if c["op"] == "read" and c["size_kb"] == 1 and c["concurrency"] == conc
            ]
            ys.append(reads[0]["throughput_req_s"])
        ax.plot(CONCURRENCIES, ys, marker="s", linewidth=2.2,
                color=COLORS[proto], label=LABELS[proto])
    ax.set_xlabel("Concurrence (nombre de requêtes)")
    ax.set_ylabel("Débit (req/s)")
    ax.set_title("Débit de lecture (GET) — payload 1 Ko")
    ax.set_xticks(CONCURRENCIES)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, "02-chart-throughput-1kb.png"), dpi=130)
    plt.close(fig)


def chart_cpu(data):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for proto in ("rest", "soap", "graphql", "grpc"):
        ys = []
        for conc in CONCURRENCIES:
            creates = [
                c for c in data[proto]
                if c["op"] == "create" and c["size_kb"] == 100 and c["concurrency"] == conc
            ]
            ys.append(creates[0]["cpu_percent"])
        ax.plot(CONCURRENCIES, ys, marker="^", linewidth=2.2,
                color=COLORS[proto], label=LABELS[proto])
    ax.set_xlabel("Concurrence (nombre de requêtes)")
    ax.set_ylabel("CPU serveur moyen (%)")
    ax.set_title("CPU serveur en création (POST) — payload 100 Ko")
    ax.set_xticks(CONCURRENCIES)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, "03-chart-cpu-100kb.png"), dpi=130)
    plt.close(fig)


def main():
    data = load()
    chart_latency(data)
    chart_throughput(data)
    chart_cpu(data)
    print("Graphiques générés dans", DOCS)


if __name__ == "__main__":
    main()
