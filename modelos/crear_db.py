import os
import sys
from sqlalchemy import create_engine

# --- Inicio del Arreglo ---
# 1. Obtener la ruta del directorio actual (modelos)
script_dir = os.path.dirname(os.path.abspath(__file__))
# 2. Subir un nivel para llegar a la raíz del proyecto (E-cites)
project_root = os.path.dirname(script_dir)
# 3. Añadir la raíz del proyecto al path de Python
sys.path.append(project_root)
# --- Fin del Arreglo ---

# Ahora, todos los imports deben ser "absolutos" desde la raíz (E-cites)
from config.bd import Base
from modelos.usuario_model import Usuario, Rol
from modelos.negocio_model import Negocio
from modelos.lugar_model import Lugar
from modelos.reserva_general_model import ReservaGeneral
from modelos.reserva_muelle import ReservaMuelle

# El resto de tu código sigue igual
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://citauser:claveSegura@localhost:5432/citasdb"
)

print(f"--- Conectando a la base de datos en: {DATABASE_URL} ---")

# Usa la variable DATABASE_URL para crear el engine
engine = create_engine(DATABASE_URL)
print("Tablas creadas correctamente.")



