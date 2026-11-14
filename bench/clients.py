"""Clients de benchmark pour les 4 protocoles.

Chaque client expose les 4 opérations CRUD avec un payload de taille donnée
(le payload est injecté dans le champ `preferences` d'une réservation).
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
from requests.adapters import HTTPAdapter

from shared.models import payload_at_size

GRPC_STUB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "grpc_svc"))
sys.path.insert(0, GRPC_STUB_PATH)
import grpc  # noqa: E402
import hotel_pb2  # noqa: E402
import hotel_pb2_grpc  # noqa: E402

NS_SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
NS_HOTEL = "http://tp182.hotel/soap"


def _http_session() -> requests.Session:
    """Session HTTP avec un grand pool : évite l'épuisement du pool urllib3
    quand de nombreux threads partagent la même session pendant le benchmark."""
    s = requests.Session()
    adapter = HTTPAdapter(pool_connections=4096, pool_maxsize=4096, max_retries=0)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


class RestClient:
    name = "REST"

    def __init__(self, base: str):
        self.base = base
        self.session = _http_session()

    def _payload(self, size_kb: int) -> str:
        return payload_at_size(size_kb)

    def setup(self, n: int, size_kb: int):
        for i in range(n):
            data = {
                "id": f"res-bench-{i}",
                "client_id": "cli-000001",
                "chambre_id": "ch-000001",
                "date_debut": "2025-08-01",
                "date_fin": "2025-08-03",
                "preferences": self._payload(size_kb),
            }
            self.session.post(f"{self.base}/api/reservations", json=data, timeout=30).raise_for_status()

    def create(self, size_kb: int, i: int):
        data = {
            "client_id": "cli-000001",
            "chambre_id": "ch-000001",
            "date_debut": "2025-08-01",
            "date_fin": "2025-08-03",
            "preferences": self._payload(size_kb),
        }
        r = self.session.post(f"{self.base}/api/reservations", json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def read(self, size_kb: int, i: int):
        r = self.session.get(f"{self.base}/api/reservations/res-000001", timeout=30)
        r.raise_for_status()
        return r.json()

    def update(self, size_kb: int, i: int):
        data = {"preferences": self._payload(size_kb)}
        r = self.session.put(f"{self.base}/api/reservations/res-000001", json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def delete(self, size_kb: int, i: int):
        r = self.session.delete(f"{self.base}/api/reservations/res-bench-{i}", timeout=30)
        r.raise_for_status()
        return r.json()


class SoapClient:
    name = "SOAP"

    def __init__(self, base: str):
        self.base = base
        self.session = _http_session()

    def _payload(self, size_kb: int) -> str:
        return payload_at_size(size_kb)

    def _call(self, op: str, args: dict) -> dict:
        env = ET.Element(f"{{{NS_SOAP_ENV}}}Envelope")
        ET.SubElement(env, f"{{{NS_SOAP_ENV}}}Header")
        body = ET.SubElement(env, f"{{{NS_SOAP_ENV}}}Body")
        op_el = ET.SubElement(body, f"{{{NS_HOTEL}}}{op}")
        for k, v in args.items():
            child = ET.SubElement(op_el, f"{{{NS_HOTEL}}}{k}")
            child.text = str(v)
        xml_str = ET.tostring(env, encoding="unicode")
        r = self.session.post(
            f"{self.base}/soap",
            data=xml_str,
            headers={"Content-Type": "text/xml"},
            timeout=30,
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
        fault = root.find(f".//{{{NS_SOAP_ENV}}}Fault")
        if fault is not None:
            raise RuntimeError(f"SOAP fault: {ET.tostring(fault, encoding='unicode')}")
        result_el = root.find(f".//{{{NS_HOTEL}}}{op}Response")
        if result_el is None:
            raise RuntimeError(f"réponse SOAP sans {op}Response")
        out = {}
        for child in result_el.iter():
            tag = child.tag.split("}")[-1]
            if child.text:
                out[tag] = child.text
        return out

    def setup(self, n: int, size_kb: int):
        for i in range(n):
            self._call("createReservation", {
                "id": f"res-bench-{i}",
                "client_id": "cli-000001",
                "chambre_id": "ch-000001",
                "date_debut": "2025-08-01",
                "date_fin": "2025-08-03",
                "preferences": self._payload(size_kb),
            })

    def create(self, size_kb: int, i: int):
        return self._call("createReservation", {
            "client_id": "cli-000001",
            "chambre_id": "ch-000001",
            "date_debut": "2025-08-01",
            "date_fin": "2025-08-03",
            "preferences": self._payload(size_kb),
        })

    def read(self, size_kb: int, i: int):
        return self._call("getReservation", {"id": "res-000001"})

    def update(self, size_kb: int, i: int):
        return self._call("updateReservation", {
            "id": "res-000001",
            "preferences": self._payload(size_kb),
        })

    def delete(self, size_kb: int, i: int):
        return self._call("deleteReservation", {"id": f"res-bench-{i}"})


class GraphQLClient:
    name = "GraphQL"

    def __init__(self, base: str):
        self.base = base
        self.session = _http_session()

    def _payload(self, size_kb: int) -> str:
        return payload_at_size(size_kb)

    def _query(self, query: str, variables: dict = None):
        r = self.session.post(
            f"{self.base}/graphql",
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        if "errors" in body:
            raise RuntimeError(f"GraphQL errors: {body['errors']}")
        return body.get("data", {})

    def setup(self, n: int, size_kb: int):
        q = """
        mutation Create($input: ReservationInput!) {
          createReservation(input: $input) { id }
        }
        """
        for i in range(n):
            variables = {
                "input": {
                    "id": f"res-bench-{i}",
                    "client_id": "cli-000001",
                    "chambre_id": "ch-000001",
                    "date_debut": "2025-08-01",
                    "date_fin": "2025-08-03",
                    "preferences": self._payload(size_kb),
                }
            }
            self._query(q, variables)

    def create(self, size_kb: int, i: int):
        q = """
        mutation Create($input: ReservationInput!) {
          createReservation(input: $input) { id }
        }
        """
        variables = {
            "input": {
                "client_id": "cli-000001",
                "chambre_id": "ch-000001",
                "date_debut": "2025-08-01",
                "date_fin": "2025-08-03",
                "preferences": self._payload(size_kb),
            }
        }
        return self._query(q, variables)

    def read(self, size_kb: int, i: int):
        q = """
        query { reservation(id: "res-000001") { id client_id chambre_id preferences } }
        """
        return self._query(q)

    def update(self, size_kb: int, i: int):
        q = """
        mutation Update($id: String!, $input: ReservationInput!) {
          updateReservation(id: $id, input: $input) { id }
        }
        """
        variables = {
            "id": "res-000001",
            "input": {
                "client_id": "cli-000001",
                "chambre_id": "ch-000001",
                "date_debut": "2025-08-01",
                "date_fin": "2025-08-03",
                "preferences": self._payload(size_kb),
            }
        }
        return self._query(q, variables)

    def delete(self, size_kb: int, i: int):
        q_del = 'mutation { deleteReservation(id: "res-bench-%d") { success } }' % i
        return self._query(q_del)


class GrpcClient:
    name = "gRPC"

    def __init__(self, target: str):
        self.channel = grpc.insecure_channel(target)
        self.stub = hotel_pb2_grpc.HotelServiceStub(self.channel)

    def _payload(self, size_kb: int) -> str:
        return payload_at_size(size_kb)

    def setup(self, n: int, size_kb: int):
        for i in range(n):
            self.stub.CreateReservation(hotel_pb2.Reservation(
                id=f"res-bench-{i}",
                client_id="cli-000001",
                chambre_id="ch-000001",
                date_debut="2025-08-01",
                date_fin="2025-08-03",
                preferences=self._payload(size_kb),
            ))

    def create(self, size_kb: int, i: int):
        return self.stub.CreateReservation(hotel_pb2.Reservation(
            client_id="cli-000001",
            chambre_id="ch-000001",
            date_debut="2025-08-01",
            date_fin="2025-08-03",
            preferences=self._payload(size_kb),
        ))

    def read(self, size_kb: int, i: int):
        return self.stub.GetReservation(hotel_pb2.IdRequest(id="res-000001"))

    def update(self, size_kb: int, i: int):
        return self.stub.UpdateReservation(hotel_pb2.Reservation(
            id="res-000001",
            client_id="cli-000001",
            chambre_id="ch-000001",
            date_debut="2025-08-01",
            date_fin="2025-08-03",
            preferences=self._payload(size_kb),
        ))

    def delete(self, size_kb: int, i: int):
        return self.stub.DeleteReservation(hotel_pb2.IdRequest(id=f"res-bench-{i}"))


def make_client(protocol: str, target: str):
    if protocol == "rest":
        return RestClient(target)
    if protocol == "soap":
        return SoapClient(target)
    if protocol == "graphql":
        return GraphQLClient(target)
    if protocol == "grpc":
        return GrpcClient(target)
    raise ValueError(f"protocole inconnu: {protocol}")
