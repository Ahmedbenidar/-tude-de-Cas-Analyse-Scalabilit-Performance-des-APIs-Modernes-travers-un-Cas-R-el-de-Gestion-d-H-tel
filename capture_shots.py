"""Capture les écrans des 4 services en fonctionnement pour le README.

Utilise Edge headless (fiable sur ce poste). Chaque service doit déjà tourner.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(BASE, "docs")
os.makedirs(DOCS, exist_ok=True)

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def shot(url: str, out: str):
    if os.path.exists(out):
        os.remove(out)
    cmd = [
        EDGE, "--headless", "--disable-gpu", "--no-sandbox",
        f"--user-data-dir={os.environ['TEMP']}\\edge-shot-{int(time.time()*1000)}",
        "--window-size=1280,900",
        f"--screenshot={out}",
        url,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    time.sleep(1.0)
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        print(f"OK  {out}")
    else:
        print(f"ERR {out}")


def main():
    shots = [
        ("http://127.0.0.1:5001/health", "01-rest-health.png"),
        ("http://127.0.0.1:5001/api/clients", "02-rest-clients.png"),
        ("http://127.0.0.1:5002/health", "03-soap-health.png"),
        ("http://127.0.0.1:5003/graphql", "04-graphql-playground.png"),
    ]
    for url, name in shots:
        try:
            shot(url, os.path.join(DOCS, name))
        except Exception as exc:
            print(f"ERR {name}: {exc}")

    # Captures de requêtes POST réelles (REST create, SOAP, GraphQL)
    try:
        import requests
        s = requests.Session()
        r = s.get("http://127.0.0.1:5001/api/clients/cli-000001", timeout=10)
        with open(os.path.join(DOCS, "05-rest-get-client.txt"), "w", encoding="utf-8") as f:
            f.write(f"GET /api/clients/cli-000001 -> {r.status_code}\n\n{r.text}\n")
        print("OK  05-rest-get-client.txt")
    except Exception as exc:
        print(f"ERR 05-rest-get-client: {exc}")

    try:
        import requests
        soap_body = """<?xml version="1.0"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:hotel="http://tp182.hotel/soap">
  <soapenv:Body>
    <hotel:getClient><id>cli-000001</id></hotel:getClient>
  </soapenv:Body>
</soapenv:Envelope>"""
        r = requests.post("http://127.0.0.1:5002/soap", data=soap_body, headers={"Content-Type": "text/xml"}, timeout=10)
        with open(os.path.join(DOCS, "06-soap-response.txt"), "w", encoding="utf-8") as f:
            f.write(f"POST /soap -> {r.status_code}\n\n{r.text}\n")
        print("OK  06-soap-response.txt")
    except Exception as exc:
        print(f"ERR 06-soap-response: {exc}")

    try:
        import requests
        gql = {"query": 'query { client(id: "cli-000001") { id nom prenom email } }'}
        r = requests.post("http://127.0.0.1:5003/graphql", json=gql, timeout=10)
        with open(os.path.join(DOCS, "07-graphql-query.txt"), "w", encoding="utf-8") as f:
            f.write(f"POST /graphql -> {r.status_code}\n\n{r.text}\n")
        print("OK  07-graphql-query.txt")
    except Exception as exc:
        print(f"ERR 07-graphql-query: {exc}")

    print("\nCaptures terminées.")


if __name__ == "__main__":
    main()
