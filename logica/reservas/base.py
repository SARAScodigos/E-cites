class ReservaBase:
    def __init__(self, db, tenant_id):
        self.db = db
        self.tenant_id = tenant_id

    def crear_reserva(self, datos):
        """
        Crea una reserva.
        Debe devolver (diccionario_respuesta, status_code)
        """
        raise NotImplementedError("Subclase debe implementar crear_reserva")

    # --- CORRECCIÓN 1 ---
    # Ahora acepta un 'usuario_id' opcional con 'None' como default.
    def listar_reservas(self, usuario_id=None):
        """
        Lista las reservas.
        Si usuario_id se provee, filtra por ese usuario.
        Si usuario_id es None, lista todas las del tenant.
        """
        raise NotImplementedError("Subclase debe implementar listar_reservas")

    # --- CORRECCIÓN 2 ---
    # Cambiado el nombre y los argumentos para que coincidan
    # con la implementación de Muelle y la llamada de app.py
    def consultar_disponibilidad_por_dias(self, fecha_inicio, fecha_fin):
        """
        Consulta la disponibilidad entre dos fechas.
        """
        raise NotImplementedError("Subclase debe implementar consultar_disponibilidad_por_dias")