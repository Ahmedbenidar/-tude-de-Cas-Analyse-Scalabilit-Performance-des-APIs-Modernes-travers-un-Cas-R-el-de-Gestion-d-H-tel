"""Service REST — Flask.

Endpoints CRUD pour Client, Chambre, Réservation.
GET /health pour le contrôle d'état.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

logging.getLogger("werkzeug").setLevel(logging.ERROR)

from flask import Flask, jsonify, request

from shared.models import DataStore

app = Flask(__name__)
store = DataStore()

API_PREFIX = "/api"


def _bad_request(msg: str):
    return jsonify({"error": msg}), 400


# ---------------------------------------------------------------- Clients
@app.route(f"{API_PREFIX}/clients", methods=["POST"])
def create_client():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("nom"):
        return _bad_request("nom requis")
    c = store.create_client(data)
    return jsonify(c.to_dict()), 201


@app.route(f"{API_PREFIX}/clients", methods=["GET"])
def list_clients():
    return jsonify([c.to_dict() for c in store.list_clients()])


@app.route(f"{API_PREFIX}/clients/<client_id>", methods=["GET"])
def get_client(client_id):
    c = store.get_client(client_id)
    if c is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(c.to_dict())


@app.route(f"{API_PREFIX}/clients/<client_id>", methods=["PUT"])
def update_client(client_id):
    data = request.get_json(force=True, silent=True) or {}
    c = store.update_client(client_id, data)
    if c is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(c.to_dict())


@app.route(f"{API_PREFIX}/clients/<client_id>", methods=["DELETE"])
def delete_client(client_id):
    if not store.delete_client(client_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"success": True})


# ---------------------------------------------------------------- Chambres
@app.route(f"{API_PREFIX}/chambres", methods=["POST"])
def create_chambre():
    data = request.get_json(force=True, silent=True) or {}
    ch = store.create_chambre(data)
    return jsonify(ch.to_dict()), 201


@app.route(f"{API_PREFIX}/chambres", methods=["GET"])
def list_chambres():
    return jsonify([ch.to_dict() for ch in store.list_chambres()])


@app.route(f"{API_PREFIX}/chambres/<chambre_id>", methods=["GET"])
def get_chambre(chambre_id):
    ch = store.get_chambre(chambre_id)
    if ch is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(ch.to_dict())


@app.route(f"{API_PREFIX}/chambres/<chambre_id>", methods=["PUT"])
def update_chambre(chambre_id):
    data = request.get_json(force=True, silent=True) or {}
    ch = store.update_chambre(chambre_id, data)
    if ch is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(ch.to_dict())


@app.route(f"{API_PREFIX}/chambres/<chambre_id>", methods=["DELETE"])
def delete_chambre(chambre_id):
    if not store.delete_chambre(chambre_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"success": True})


# ---------------------------------------------------------------- Reservations
@app.route(f"{API_PREFIX}/reservations", methods=["POST"])
def create_reservation():
    data = request.get_json(force=True, silent=True) or {}
    if not data.get("client_id") or not data.get("chambre_id"):
        return _bad_request("client_id et chambre_id requis")
    r = store.create_reservation(data)
    return jsonify(r.to_dict()), 201


@app.route(f"{API_PREFIX}/reservations", methods=["GET"])
def list_reservations():
    return jsonify([r.to_dict() for r in store.list_reservations()])


@app.route(f"{API_PREFIX}/reservations/<reservation_id>", methods=["GET"])
def get_reservation(reservation_id):
    r = store.get_reservation(reservation_id)
    if r is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(r.to_dict())


@app.route(f"{API_PREFIX}/reservations/<reservation_id>", methods=["PUT"])
def update_reservation(reservation_id):
    data = request.get_json(force=True, silent=True) or {}
    r = store.update_reservation(reservation_id, data)
    if r is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(r.to_dict())


@app.route(f"{API_PREFIX}/reservations/<reservation_id>", methods=["DELETE"])
def delete_reservation(reservation_id):
    if not store.delete_reservation(reservation_id):
        return jsonify({"error": "not found"}), 404
    return jsonify({"success": True})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "rest"})


if __name__ == "__main__":
    from waitress import serve

    port = int(os.environ.get("PORT", "5001"))
    print(f"REST server listening on 127.0.0.1:{port}", flush=True)
    serve(app, host="127.0.0.1", port=port, threads=64)
