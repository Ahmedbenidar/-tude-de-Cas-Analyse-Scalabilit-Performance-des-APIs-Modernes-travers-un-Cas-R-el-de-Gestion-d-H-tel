"""Service gRPC — grpcio + stubs générés.

Expose toutes les méthodes du proto hotel.proto. Le DataStore partagé assure
des données identiques aux autres protocoles.
"""
from __future__ import annotations

import os
import sys
from concurrent import futures

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.dirname(__file__))

import grpc

import hotel_pb2
import hotel_pb2_grpc
from shared.models import DataStore

store = DataStore()


def _to_pb_client(c) -> hotel_pb2.Client:
    return hotel_pb2.Client(
        id=c.id, nom=c.nom, prenom=c.prenom, email=c.email, telephone=c.telephone
    )


def _to_pb_chambre(ch) -> hotel_pb2.Chambre:
    return hotel_pb2.Chambre(id=ch.id, type=ch.type, prix=ch.prix, disponible=ch.disponible)


def _to_pb_reservation(r) -> hotel_pb2.Reservation:
    return hotel_pb2.Reservation(
        id=r.id,
        client_id=r.client_id,
        chambre_id=r.chambre_id,
        date_debut=r.date_debut,
        date_fin=r.date_fin,
        preferences=r.preferences,
    )


class HotelServicer(hotel_pb2_grpc.HotelServiceServicer):
    # Clients
    def CreateClient(self, request, context):
        c = store.create_client(
            {
                "id": request.id or None,
                "nom": request.nom,
                "prenom": request.prenom,
                "email": request.email,
                "telephone": request.telephone,
            }
        )
        return _to_pb_client(c)

    def GetClient(self, request, context):
        c = store.get_client(request.id)
        if c is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "client introuvable")
        return _to_pb_client(c)

    def ListClients(self, request, context):
        return hotel_pb2.ClientList(clients=[_to_pb_client(c) for c in store.list_clients()])

    def UpdateClient(self, request, context):
        c = store.update_client(
            request.id,
            {
                "nom": request.nom,
                "prenom": request.prenom,
                "email": request.email,
                "telephone": request.telephone,
            },
        )
        if c is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "client introuvable")
        return _to_pb_client(c)

    def DeleteClient(self, request, context):
        return hotel_pb2.DeleteResponse(success=store.delete_client(request.id))

    # Chambres
    def CreateChambre(self, request, context):
        ch = store.create_chambre(
            {
                "id": request.id or None,
                "type": request.type,
                "prix": request.prix,
                "disponible": request.disponible,
            }
        )
        return _to_pb_chambre(ch)

    def GetChambre(self, request, context):
        ch = store.get_chambre(request.id)
        if ch is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "chambre introuvable")
        return _to_pb_chambre(ch)

    def ListChambres(self, request, context):
        return hotel_pb2.ChambreList(chambres=[_to_pb_chambre(ch) for ch in store.list_chambres()])

    def UpdateChambre(self, request, context):
        ch = store.update_chambre(
            request.id,
            {"type": request.type, "prix": request.prix, "disponible": request.disponible},
        )
        if ch is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "chambre introuvable")
        return _to_pb_chambre(ch)

    def DeleteChambre(self, request, context):
        return hotel_pb2.DeleteResponse(success=store.delete_chambre(request.id))

    # Reservations
    def CreateReservation(self, request, context):
        r = store.create_reservation(
            {
                "id": request.id or None,
                "client_id": request.client_id,
                "chambre_id": request.chambre_id,
                "date_debut": request.date_debut,
                "date_fin": request.date_fin,
                "preferences": request.preferences,
            }
        )
        return _to_pb_reservation(r)

    def GetReservation(self, request, context):
        r = store.get_reservation(request.id)
        if r is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "reservation introuvable")
        return _to_pb_reservation(r)

    def ListReservations(self, request, context):
        return hotel_pb2.ReservationList(
            reservations=[_to_pb_reservation(r) for r in store.list_reservations()]
        )

    def UpdateReservation(self, request, context):
        r = store.update_reservation(
            request.id,
            {
                "client_id": request.client_id,
                "chambre_id": request.chambre_id,
                "date_debut": request.date_debut,
                "date_fin": request.date_fin,
                "preferences": request.preferences,
            },
        )
        if r is None:
            context.abort(grpc.StatusCode.NOT_FOUND, "reservation introuvable")
        return _to_pb_reservation(r)

    def DeleteReservation(self, request, context):
        return hotel_pb2.DeleteResponse(success=store.delete_reservation(request.id))


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    hotel_pb2_grpc.add_HotelServiceServicer_to_server(HotelServicer(), server)
    port = os.environ.get("PORT", "5004")
    server.add_insecure_port(f"127.0.0.1:{port}")
    server.start()
    print(f"gRPC server listening on 127.0.0.1:{port}", flush=True)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
