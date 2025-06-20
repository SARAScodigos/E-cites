
class ReservaBase:
    def __init__(self, db, tenant_id):
        self.db = db
        self.tenant_id = tenant_id

    def crear_reserva(self, datos):
        raise NotImplementedError()

    def listar_reservas(self):
        raise NotImplementedError()

    def consultar_disponibilidad(self):
        raise NotImplementedError()