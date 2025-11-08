# En modelos/lugar_model.py

from sqlalchemy import Column, Integer, String, ForeignKey
from config.bd import Base

class Lugar(Base):
    __tablename__ = "lugares"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    capacidad = Column(Integer, nullable=False)
    zona = Column(String(100), nullable=True)
    tipo = Column(String(50), nullable=True) # ej: 'muelle', 'estetica'
    
    # Clave foránea para vincularlo al negocio (tenant)
    tenant_id = Column(Integer, ForeignKey("negocios.id"), nullable=False)