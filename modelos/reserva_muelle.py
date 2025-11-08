from sqlalchemy import Column, Integer, String, ForeignKey, Date, Boolean
from config.bd import Base

class ReservaMuelle(Base):
    __tablename__ = "reservas_muelle"

    # --- Columnas deducidas de tus INSERTs y UPDATEs ---

    # Esta es la llave primaria Y la llave foránea a la vez.
    # Crea una relación 1 a 1 con reservas_generales.
    reserva_id = Column(Integer, ForeignKey("reservas_generales.id"), primary_key=True)

    # Columnas de fechas (usamos Date por tu lógica)
    fecha_entrada = Column(Date, nullable=False)
    fecha_salida = Column(Date, nullable=False)

    # Columna de texto (ej: "Yate", "Bote")
    tipo_embarcacion = Column(String(100), nullable=False)

    # Columnas booleanas (tus .get("...", False))
    requiere_pintura = Column(Boolean, nullable=False, default=False)
    requiere_mecanica = Column(Boolean, nullable=False, default=False)
    requiere_motor = Column(Boolean, nullable=False, default=False)