# logica/reservas/factory.py

from .muelle import ReservaMuelle
from .hotel import ReservaHotel
from .restaurante import ReservaRestaurante

def obtener_reserva_handler(tipo_negocio, db, tenant_id):
    if tipo_negocio == "muelle":
        return ReservaMuelle(db, tenant_id)
    elif tipo_negocio == "hotel":
        return ReservaHotel(db, tenant_id)
    elif tipo_negocio == "restaurante":
        return ReservaRestaurante(db, tenant_id)
    else:
        raise ValueError("Tipo de negocio no soportado")
