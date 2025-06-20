from abc import ABC, abstractmethod

class AdminReservaBase(ABC):
    def __init__(self, db, tenant_id):
        self.db = db
        self.tenant_id = tenant_id

    @abstractmethod
    def crear_reserva(self, datos):
        pass

    @abstractmethod
    def editar_reserva(self, reserva_id, datos):
        pass

    @abstractmethod
    def eliminar_reserva(self, reserva_id):
        pass
    
    @abstractmethod
    def listar_reserva(self):
        pass
    