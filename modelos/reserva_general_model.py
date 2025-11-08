from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.sql import func
from config.bd import Base

class ReservaGeneral(Base):
    __tablename__ = "reservas_generales"

    # 'id' es el 'reserva_id' en la tabla hija
    id = Column(Integer, primary_key=True)

    # --- Columnas deducidas de tus INSERTs y JOINs ---
    
    # Llave foránea a la tabla usuarios
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # Llave foránea a la tabla lugares
    lugar_id = Column(Integer, ForeignKey("lugares.id"), nullable=False)
    
    # Llave foránea al negocio (tenant)
    tenant_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)
    
    # 'fecha' se usa en tus INSERTs (ej: datetime.now().date())
    # Usamos Date ya que no parece importar la hora.
    fecha = Column(Date, nullable=False, default=func.now())