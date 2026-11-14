"""Modèle de données partagé pour le TP18x (comparaison REST / SOAP / GraphQL / gRPC).

Chaque service embarque sa propre instance en mémoire. Le stockage est identique
pour les 4 protocoles afin que les mesures soient comparables.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@dataclass
class Client:
    id: str = field(default_factory=lambda: _new_id("cli"))
    nom: str = "Dupont"
    prenom: str = "Jean"
    email: str = "jean.dupont@example.com"
    telephone: str = "+212600000000"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Chambre:
    id: str = field(default_factory=lambda: _new_id("ch"))
    type: str = "standard"
    prix: float = 100.0
    disponible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Reservation:
    id: str = field(default_factory=lambda: _new_id("res"))
    client_id: str = ""
    chambre_id: str = ""
    date_debut: str = "2025-01-01"
    date_fin: str = "2025-01-03"
    preferences: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def payload_at_size(size_kb: int) -> str:
    """Génère un texte de préférences dont la taille cible (en Ko) est atteinte.

    Les tailles 1 Ko / 10 Ko / 100 Ko correspondent au scénario de test du lab.
    """
    unit = "Allergies: aucune; Vue: mer; Lit: double; Parking: oui; Petit-dejeuner: inclus. "
    target = max(0, size_kb * 1024)
    reps = (target // len(unit)) + 1
    return (unit * reps)[:target]


class DataStore:
    """Stockage en mémoire, thread-safe, avec pré-remplissage."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.clients: Dict[str, Client] = {}
        self.chambres: Dict[str, Chambre] = {}
        self.reservations: Dict[str, Reservation] = {}
        self._seed()

    def _seed(self) -> None:
        clients = [
            Client("cli-000001", "Benidar", "Ahmed", "ahmed.benidar@example.com", "+212611111111"),
            Client("cli-000002", "El Amrani", "Sara", "sara.elamrani@example.com", "+212622222222"),
            Client("cli-000003", "Tazi", "Karim", "karim.tazi@example.com", "+212633333333"),
        ]
        chambres = [
            Chambre("ch-000001", "standard", 80.0, True),
            Chambre("ch-000002", "double", 120.0, True),
            Chambre("ch-000003", "suite", 250.0, False),
        ]
        reservations = [
            Reservation("res-000001", "cli-000001", "ch-000001", "2025-06-01", "2025-06-04", "Vue mer"),
            Reservation("res-000002", "cli-000002", "ch-000002", "2025-06-10", "2025-06-12", "Lit double"),
        ]
        for c in clients:
            self.clients[c.id] = c
        for ch in chambres:
            self.chambres[ch.id] = ch
        for r in reservations:
            self.reservations[r.id] = r

    # --- Clients ---
    def create_client(self, data: Dict[str, Any]) -> Client:
        c = Client(
            id=data.get("id") or _new_id("cli"),
            nom=data.get("nom", "Dupont"),
            prenom=data.get("prenom", "Jean"),
            email=data.get("email", "jean.dupont@example.com"),
            telephone=data.get("telephone", "+212600000000"),
        )
        with self._lock:
            self.clients[c.id] = c
        return c

    def get_client(self, client_id: str) -> Optional[Client]:
        with self._lock:
            return self.clients.get(client_id)

    def list_clients(self) -> List[Client]:
        with self._lock:
            return list(self.clients.values())

    def update_client(self, client_id: str, data: Dict[str, Any]) -> Optional[Client]:
        with self._lock:
            c = self.clients.get(client_id)
            if c is None:
                return None
            for key in ("nom", "prenom", "email", "telephone"):
                if key in data:
                    setattr(c, key, data[key])
            return c

    def delete_client(self, client_id: str) -> bool:
        with self._lock:
            return self.clients.pop(client_id, None) is not None

    # --- Chambres ---
    def create_chambre(self, data: Dict[str, Any]) -> Chambre:
        ch = Chambre(
            id=data.get("id") or _new_id("ch"),
            type=data.get("type", "standard"),
            prix=float(data.get("prix", 100.0)),
            disponible=bool(data.get("disponible", True)),
        )
        with self._lock:
            self.chambres[ch.id] = ch
        return ch

    def get_chambre(self, chambre_id: str) -> Optional[Chambre]:
        with self._lock:
            return self.chambres.get(chambre_id)

    def list_chambres(self) -> List[Chambre]:
        with self._lock:
            return list(self.chambres.values())

    def update_chambre(self, chambre_id: str, data: Dict[str, Any]) -> Optional[Chambre]:
        with self._lock:
            ch = self.chambres.get(chambre_id)
            if ch is None:
                return None
            if "type" in data:
                ch.type = data["type"]
            if "prix" in data:
                ch.prix = float(data["prix"])
            if "disponible" in data:
                ch.disponible = bool(data["disponible"])
            return ch

    def delete_chambre(self, chambre_id: str) -> bool:
        with self._lock:
            return self.chambres.pop(chambre_id, None) is not None

    # --- Reservations ---
    def create_reservation(self, data: Dict[str, Any]) -> Reservation:
        r = Reservation(
            id=data.get("id") or _new_id("res"),
            client_id=data.get("client_id", ""),
            chambre_id=data.get("chambre_id", ""),
            date_debut=data.get("date_debut", "2025-01-01"),
            date_fin=data.get("date_fin", "2025-01-03"),
            preferences=data.get("preferences", ""),
        )
        with self._lock:
            self.reservations[r.id] = r
        return r

    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        with self._lock:
            return self.reservations.get(reservation_id)

    def list_reservations(self) -> List[Reservation]:
        with self._lock:
            return list(self.reservations.values())

    def update_reservation(self, reservation_id: str, data: Dict[str, Any]) -> Optional[Reservation]:
        with self._lock:
            r = self.reservations.get(reservation_id)
            if r is None:
                return None
            for key in ("client_id", "chambre_id", "date_debut", "date_fin", "preferences"):
                if key in data:
                    setattr(r, key, data[key])
            return r

    def delete_reservation(self, reservation_id: str) -> bool:
        with self._lock:
            return self.reservations.pop(reservation_id, None) is not None
