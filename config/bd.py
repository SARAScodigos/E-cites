# En config/bd.py
import os # <-- ¡Añade esta línea!
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Lee la URL de la BD desde una variable de entorno
# 2. Si no la encuentra, usa la de 'localhost' (para cuando corres sin Docker)
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://citauser:claveSegura@localhost:5432/citasdb"
)

print(f"--- Conectando a la base de datos en: {DATABASE_URL} ---")

# Usa la variable DATABASE_URL para crear el engine
engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()