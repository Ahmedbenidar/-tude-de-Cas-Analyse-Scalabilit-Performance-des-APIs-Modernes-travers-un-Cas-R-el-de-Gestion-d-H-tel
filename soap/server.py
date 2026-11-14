"""Service SOAP — implémentation SOAP 1.1 native via Flask.

Expose un endpoint POST /soap qui traite les enveloppes SOAP. Le stockage est
le même DataStore partagé. Aucune dépendance externe (pas de Spyne) : le XML
SOAP est produit et consommé manuellement, ce qui rend le service portable et
déterministe pour le benchmark.
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import logging

logging.getLogger("werkzeug").setLevel(logging.ERROR)

from flask import Flask, Response, request

from shared.models import DataStore

app = Flask(__name__)
store = DataStore()

NS_SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
NS_HOTEL = "http://tp182.hotel/soap"
ET.register_namespace("soapenv", NS_SOAP_ENV)
ET.register_namespace("hotel", NS_HOTEL)


def _soap_fault(message: str) -> Response:
    env = ET.Element(f"{{{NS_SOAP_ENV}}}Envelope")
    body = ET.SubElement(env, f"{{{NS_SOAP_ENV}}}Body")
    fault = ET.SubElement(body, f"{{{NS_SOAP_ENV}}}Fault")
    fcode = ET.SubElement(fault, "faultcode")
    fcode.text = "soapenv:Server"
    fstring = ET.SubElement(fault, "faultstring")
    fstring.text = message
    return Response(
        ET.tostring(env, encoding="unicode", xml_declaration=True),
        status=500,
        mimetype="text/xml",
    )


def _text(parent: ET.Element, name: str, value: Any) -> None:
    el = ET.SubElement(parent, f"{{{NS_HOTEL}}}{name}")
    el.text = str(value) if value is not None else ""


def _dict_element(name: str, obj: Dict[str, Any]) -> ET.Element:
    el = ET.Element(f"{{{NS_HOTEL}}}{name}")
    for key, value in obj.items():
        _text(el, key, value)
    return el


def _soap_response(name: str, payload: ET.Element) -> Response:
    env = ET.Element(f"{{{NS_SOAP_ENV}}}Envelope")
    body = ET.SubElement(env, f"{{{NS_SOAP_ENV}}}Body")
    result = ET.SubElement(body, f"{{{NS_HOTEL}}}{name}Response")
    result.append(payload)
    return Response(
        ET.tostring(env, encoding="unicode", xml_declaration=True),
        mimetype="text/xml",
    )


def _parse_body(raw: bytes):
    """Retourne (opération, dict d'arguments)."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise ValueError("XML invalide")

    body = root.find(f"{{{NS_SOAP_ENV}}}Body")
    if body is None:
        raise ValueError("Body absent")
    op_el = list(body)[0] if len(body) else None
    if op_el is None:
        raise ValueError("Opération absente")

    op = op_el.tag.split("}")[-1]
    args: Dict[str, Any] = {}
    for child in op_el:
        args[child.tag.split("}")[-1]] = child.text or ""
    return op, args


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")


@app.route("/soap", methods=["POST"])
def soap_endpoint():
    try:
        op, args = _parse_body(request.data)
    except ValueError as exc:
        return _soap_fault(str(exc))

    try:
        if op == "createClient":
            obj = store.create_client(args)
            return _soap_response("createClient", _dict_element("client", obj.to_dict()))
        if op == "getClient":
            c = store.get_client(args.get("id", ""))
            if c is None:
                return _soap_fault("client introuvable")
            return _soap_response("getClient", _dict_element("client", c.to_dict()))
        if op == "listClients":
            clients = ET.Element(f"{{{NS_HOTEL}}}clients")
            for c in store.list_clients():
                clients.append(_dict_element("client", c.to_dict()))
            return _soap_response("listClients", clients)
        if op == "updateClient":
            c = store.update_client(args.get("id", ""), args)
            if c is None:
                return _soap_fault("client introuvable")
            return _soap_response("updateClient", _dict_element("client", c.to_dict()))
        if op == "deleteClient":
            ok = store.delete_client(args.get("id", ""))
            result = ET.Element(f"{{{NS_HOTEL}}}success")
            result.text = "true" if ok else "false"
            return _soap_response("deleteClient", result)

        if op == "createChambre":
            obj = store.create_chambre(args)
            return _soap_response("createChambre", _dict_element("chambre", obj.to_dict()))
        if op == "getChambre":
            ch = store.get_chambre(args.get("id", ""))
            if ch is None:
                return _soap_fault("chambre introuvable")
            return _soap_response("getChambre", _dict_element("chambre", ch.to_dict()))
        if op == "listChambres":
            chambres = ET.Element(f"{{{NS_HOTEL}}}chambres")
            for ch in store.list_chambres():
                chambres.append(_dict_element("chambre", ch.to_dict()))
            return _soap_response("listChambres", chambres)
        if op == "updateChambre":
            ch = store.update_chambre(args.get("id", ""), args)
            if ch is None:
                return _soap_fault("chambre introuvable")
            return _soap_response("updateChambre", _dict_element("chambre", ch.to_dict()))
        if op == "deleteChambre":
            ok = store.delete_chambre(args.get("id", ""))
            result = ET.Element(f"{{{NS_HOTEL}}}success")
            result.text = "true" if ok else "false"
            return _soap_response("deleteChambre", result)

        if op == "createReservation":
            obj = store.create_reservation(args)
            return _soap_response("createReservation", _dict_element("reservation", obj.to_dict()))
        if op == "getReservation":
            r = store.get_reservation(args.get("id", ""))
            if r is None:
                return _soap_fault("reservation introuvable")
            return _soap_response("getReservation", _dict_element("reservation", r.to_dict()))
        if op == "listReservations":
            reservations = ET.Element(f"{{{NS_HOTEL}}}reservations")
            for r in store.list_reservations():
                reservations.append(_dict_element("reservation", r.to_dict()))
            return _soap_response("listReservations", reservations)
        if op == "updateReservation":
            r = store.update_reservation(args.get("id", ""), args)
            if r is None:
                return _soap_fault("reservation introuvable")
            return _soap_response("updateReservation", _dict_element("reservation", r.to_dict()))
        if op == "deleteReservation":
            ok = store.delete_reservation(args.get("id", ""))
            result = ET.Element(f"{{{NS_HOTEL}}}success")
            result.text = "true" if ok else "false"
            return _soap_response("deleteReservation", result)

        return _soap_fault(f"opération inconnue: {op}")
    except Exception as exc:  # garde-fou: ne jamais faire tomber le serveur
        return _soap_fault(f"erreur interne: {exc}")


@app.route("/health")
def health():
    return "ok"


if __name__ == "__main__":
    from waitress import serve

    port = int(os.environ.get("PORT", "5002"))
    print(f"SOAP server listening on 127.0.0.1:{port}", flush=True)
    serve(app, host="127.0.0.1", port=port, threads=64)
