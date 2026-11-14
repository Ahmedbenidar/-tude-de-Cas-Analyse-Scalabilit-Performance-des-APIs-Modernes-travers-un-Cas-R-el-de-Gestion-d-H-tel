"""Service GraphQL — Ariadne.

Schema CRUD pour Client, Chambre, Réservation. Ariadne expose /graphql (POST)
et le Playground GraphQL est activé en GET pour la capture d'écran.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

logging.getLogger("werkzeug").setLevel(logging.ERROR)

from ariadne import MutationType, QueryType, gql, graphql_sync, make_executable_schema
from flask import Flask, Response, request

from shared.models import DataStore

app = Flask(__name__)
store = DataStore()

type_defs = gql(
    """
    type Client {
        id: String!
        nom: String!
        prenom: String!
        email: String!
        telephone: String!
    }

    type Chambre {
        id: String!
        type: String!
        prix: Float!
        disponible: Boolean!
    }

    type Reservation {
        id: String!
        client_id: String!
        chambre_id: String!
        date_debut: String!
        date_fin: String!
        preferences: String!
    }

    type DeleteResult {
        success: Boolean!
    }

    input ClientInput {
        id: String
        nom: String!
        prenom: String!
        email: String!
        telephone: String!
    }

    input ChambreInput {
        id: String
        type: String!
        prix: Float!
        disponible: Boolean!
    }

    input ReservationInput {
        id: String
        client_id: String!
        chambre_id: String!
        date_debut: String!
        date_fin: String!
        preferences: String!
    }

    type Query {
        client(id: String!): Client
        clients: [Client!]!
        chambre(id: String!): Chambre
        chambres: [Chambre!]!
        reservation(id: String!): Reservation
        reservations: [Reservation!]!
    }

    type Mutation {
        createClient(input: ClientInput!): Client!
        updateClient(id: String!, input: ClientInput!): Client
        deleteClient(id: String!): DeleteResult!
        createChambre(input: ChambreInput!): Chambre!
        updateChambre(id: String!, input: ChambreInput!): Chambre
        deleteChambre(id: String!): DeleteResult!
        createReservation(input: ReservationInput!): Reservation!
        updateReservation(id: String!, input: ReservationInput!): Reservation
        deleteReservation(id: String!): DeleteResult!
    }
    """
)

query = QueryType()
mutation = MutationType()


@query.field("client")
def resolve_client(_, info, id):
    c = store.get_client(id)
    return c.to_dict() if c else None


@query.field("clients")
def resolve_clients(_, info):
    return [c.to_dict() for c in store.list_clients()]


@query.field("chambre")
def resolve_chambre(_, info, id):
    ch = store.get_chambre(id)
    return ch.to_dict() if ch else None


@query.field("chambres")
def resolve_chambres(_, info):
    return [ch.to_dict() for ch in store.list_chambres()]


@query.field("reservation")
def resolve_reservation(_, info, id):
    r = store.get_reservation(id)
    return r.to_dict() if r else None


@query.field("reservations")
def resolve_reservations(_, info):
    return [r.to_dict() for r in store.list_reservations()]


@mutation.field("createClient")
def resolve_create_client(_, info, input):
    return store.create_client(input).to_dict()


@mutation.field("updateClient")
def resolve_update_client(_, info, id, input):
    c = store.update_client(id, input)
    return c.to_dict() if c else None


@mutation.field("deleteClient")
def resolve_delete_client(_, info, id):
    return {"success": store.delete_client(id)}


@mutation.field("createChambre")
def resolve_create_chambre(_, info, input):
    return store.create_chambre(input).to_dict()


@mutation.field("updateChambre")
def resolve_update_chambre(_, info, id, input):
    ch = store.update_chambre(id, input)
    return ch.to_dict() if ch else None


@mutation.field("deleteChambre")
def resolve_delete_chambre(_, info, id):
    return {"success": store.delete_chambre(id)}


@mutation.field("createReservation")
def resolve_create_reservation(_, info, input):
    return store.create_reservation(input).to_dict()


@mutation.field("updateReservation")
def resolve_update_reservation(_, info, id, input):
    r = store.update_reservation(id, input)
    return r.to_dict() if r else None


@mutation.field("deleteReservation")
def resolve_delete_reservation(_, info, id):
    return {"success": store.delete_reservation(id)}


schema = make_executable_schema(type_defs, query, mutation)


@app.route("/graphql", methods=["GET"])
def playground():
    html = """<!doctype html>
<html><head><title>GraphQL Playground — TP182</title></head>
<body style="font-family:sans-serif;padding:2rem;background:#17212b;color:#eee">
<h1>GraphQL Playground</h1>
<p>Service GraphQL opérationnel. Envoyez vos requêtes via <code>POST /graphql</code>.</p>
<pre style="background:#0e1621;padding:1rem;border-radius:8px">
mutation {
  createReservation(input: {
    client_id: "cli-000001",
    chambre_id: "ch-000001",
    date_debut: "2025-07-01",
    date_fin: "2025-07-05",
    preferences: "Vue mer"
  }) { id client_id chambre_id }
}
</pre>
</body></html>"""
    return html


@app.route("/graphql", methods=["POST"])
def graphql():
    data = request.get_json(force=True, silent=True) or {}
    success, result = graphql_sync(schema, data, debug=True)
    return Response(
        json.dumps(result),
        status=200 if success else 400,
        mimetype="application/json",
    )


@app.route("/health")
def health():
    return json.dumps({"status": "ok", "service": "graphql"})


if __name__ == "__main__":
    from waitress import serve

    port = int(os.environ.get("PORT", "5003"))
    print(f"GraphQL server listening on 127.0.0.1:{port}", flush=True)
    serve(app, host="127.0.0.1", port=port, threads=64)
