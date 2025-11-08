# En E-cites/init_db.py
import time
import bcrypt
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.sql import text

# Importa todo lo necesario de tu proyecto
from config.bd import engine, Base, SessionLocal
from modelos.negocio_model import Negocio
from modelos.usuario_model import Usuario, Rol
from modelos.lugar_model import Lugar
from modelos.reserva_general_model import ReservaGeneral
from modelos.reserva_muelle import ReservaMuelle

# --- DEFINE TUS DATOS INICIALES AQUÍ ---
ADMIN_EMAIL = "admin@systempiura.com"
ADMIN_CLAVE = "admin123"
NEGOCIO_NOMBRE = "Muelle Principal"
NEGOCIO_TIPO = "muelle"

def inicializar_base_de_datos():
    print("--- Iniciando script de inicialización de BD ---")
    
    # 1. ESPERAR A QUE LA BASE DE DATOS ESTÉ LISTA
    # ---------------------------------------------
    conectado = False
    intentos = 0
    max_intentos = 10
    
    while not conectado and intentos < max_intentos:
        try:
            # Intenta conectarse
            conn = engine.connect()
            conn.close()
            conectado = True
            print("✅ ¡Conexión con PostgreSQL exitosa!")
        except OperationalError:
            intentos += 1
            print(f"PostgreSQL no está listo... (intento {intentos}/{max_intentos}). Reintentando en 3 segundos...")
            time.sleep(3)
            
    if not conectado:
        print("❌ No se pudo conectar a la base de datos. Abortando.")
        return

    # 2. CREAR EL ESQUEMA (TODAS TUS TABLAS)
    # ---------------------------------------------
    try:
        print("Creando todas las tablas (Base.metadata.create_all)...")
        # Esto crea todas las tablas de los modelos que importaste
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas creadas (o ya existían).")
    except Exception as e:
        print(f"❌ Error al crear tablas: {e}")
        return

    # 3. "SEMBRAR" DATOS INICIALES (Roles, Negocio, Admin)
    # ---------------------------------------------
    db = SessionLocal()
    try:
        print("Sembrando datos iniciales (roles, negocio, admin)...")
        
        # --- Crear Roles ---
        rol_usuario = db.query(Rol).filter_by(id=1).first()
        if not rol_usuario:
            db.add(Rol(id=1, nombre="usuario"))
            print("  -> Rol 'usuario' (id 1) creado.")
            
        rol_admin = db.query(Rol).filter_by(id=2).first()
        if not rol_admin:
            db.add(Rol(id=2, nombre="admin"))
            print("  -> Rol 'admin' (id 2) creado.")
            
        # --- Crear Negocio Principal (Tenant 1) ---
        negocio_principal = db.query(Negocio).filter_by(id=1).first()
        if not negocio_principal:
            db.add(Negocio(id=1, nombre=NEGOCIO_NOMBRE, tipo=NEGOCIO_TIPO))
            print(f"  -> Negocio '{NEGOCIO_NOMBRE}' (id 1) creado.")
            
        # --- Crear Usuario Administrador ---
        admin_user = db.query(Usuario).filter_by(correo=ADMIN_EMAIL).first()
        if not admin_user:
            clave_hash = bcrypt.hashpw(ADMIN_CLAVE.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            db.add(Usuario(
                nombre="Admin General",
                correo=ADMIN_EMAIL,
                clave=clave_hash,
                rol_id=2,      # ID del rol 'admin'
                tenant_id=1    # ID del negocio principal
            ))
            print(f"  -> Usuario Admin '{ADMIN_EMAIL}' creado.")
            
        # Si todo salió bien, guarda los cambios
        db.commit()
        print("✅ ¡Base de datos inicializada y sembrada con éxito!")

    except IntegrityError:
        db.rollback()
        print("ℹ️  Los datos iniciales ya existían (IntegrityError).")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al sembrar datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    # Esto te permite correrlo manualmente si quieres
    # python init_db.py
    inicializar_base_de_datos()