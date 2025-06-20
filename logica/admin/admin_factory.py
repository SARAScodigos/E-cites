from .muelle_admin import AdminReservaMuelle
# from .hotel_admin import AdminReservaHotel
# from .restaurante_admin import AdminReservaRestaurante

def obtener_admin_handler(tipo_negocio, db, tenant_id):
    if tipo_negocio is None:
        raise ValueError("El tipo de negocio no puede ser None. Verifica que el tenant_id existe en la tabla negocios.")
    
    tipo = tipo_negocio.strip().lower()

    if tipo == "muelle":
        return AdminReservaMuelle(db, tenant_id)

    raise ValueError(f"Tipo de negocio no soportado para administración: {tipo}")