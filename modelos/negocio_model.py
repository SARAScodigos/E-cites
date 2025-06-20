from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from config.bd import Base

class Negocio(Base):
    __tablename__ = "negocios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(255), nullable=True)
