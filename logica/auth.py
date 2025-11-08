from flask import Blueprint, request, jsonify
from config.bd import SessionLocal
from modelos.usuario_model import Usuario
from modelos.negocio_model import Negocio
from sqlalchemy import text
import bcrypt
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

# --- AÑADE ESTA IMPORTACIÓN ---
import traceback

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/registro", methods=["POST"])
@jwt_required()
def registro():
    # --- LOG AÑADIDO ---
    print("\n--- INICIO: Intento de Registro de Usuario ---")
    
    identidad = get_jwt_identity()
    claims = get_jwt()

    if claims['rol_id'] != 2:
        # --- LOG AÑADIDO ---
        print(f">>> ERROR: Registro denegado. No es admin (rol_id: {claims['rol_id']}).")
        return jsonify({"mensaje": "Solo administradores pueden registrar usuarios"}), 403

    datos = request.get_json()
    # --- LOG AÑADIDO ---
    print(f">>> Datos recibidos: {datos}")

    nombre = datos.get("nombre")
    correo = datos.get("correo")
    clave = datos.get("clave")

    if not nombre or not correo or not clave:
        # --- LOG AÑADIDO ---
        print(">>> ERROR: Faltan datos (nombre, correo o clave).")
        return jsonify({"mensaje": "Faltan datos"}), 400

    db = SessionLocal()
    try:
        existe = db.query(Usuario).filter_by(correo=correo).first()
        if existe:
            # --- LOG AÑADIDO ---
            print(f">>> ERROR: Correo ya existe: {correo}")
            return jsonify({"mensaje": "El correo ya está registrado"}), 409

        # --- LOG AÑADIDO ---
        print(f">>> Hasheando clave para: {nombre}")
        hashed_pw = bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt())

        nuevo_usuario = Usuario(
            nombre=nombre,
            correo=correo,
            clave=hashed_pw.decode("utf-8"),
            rol_id=1,  # usuario normal
            tenant_id=claims['tenant_id']
        )
        db.add(nuevo_usuario)
        db.commit()
        
        # --- LOG AÑADIDO ---
        print(f"✅ ÉXITO: Usuario registrado: {correo}")
        return jsonify({"mensaje": "Usuario registrado exitosamente"})

    except Exception as e:
        db.rollback()
        
        # --- LOGS AÑADIDOS (LOS MÁS IMPORTANTES) ---
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"❌ ERROR 500 en /api/registro: {e}")
        traceback.print_exc()  # <-- Esto imprimirá el error real
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        
        return jsonify({"mensaje": "Error interno", "error": str(e)}), 500
    finally:
        db.close()

@auth_bp.route("/api/login", methods=["POST"])
def login():
    # --- LOG AÑADIDO ---
    print("\n--- INICIO: Intento de Login ---")
    
    datos = request.get_json()
    correo = datos.get("correo")
    clave = datos.get("clave")

    # --- LOG AÑADIDO ---
    print(f">>> Credenciales recibidas para: {correo}")

    if not correo or not clave:
        # --- LOG AÑADIDO ---
        print(">>> ERROR: Faltan datos (correo o clave).")
        return jsonify({"mensaje": "Faltan datos"}), 400

    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter_by(correo=correo).first()
        if usuario and bcrypt.checkpw(clave.encode("utf-8"), usuario.clave.encode("utf-8")):
            access_token = create_access_token(
                identity=str(usuario.id),
                additional_claims={
                    "rol_id": usuario.rol_id,
                    "tenant_id": usuario.tenant_id
                }
            )
            # --- LOG AÑADIDO ---
            print(f"✅ ÉXITO: Login correcto para: {correo}")
            return jsonify({"mensaje": "Login exitoso", "access_token": access_token})
        else:
            # --- LOG AÑADIDO ---
            print(f">>> ERROR: Credenciales incorrectas para: {correo}")
            return jsonify({"mensaje": "Credenciales incorrectas"}), 401
            
    except Exception as e:
        # --- BLOQUE TRY/EXCEPT AÑADIDO (BUENA PRÁCTICA) ---
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"❌ ERROR 500 en /api/login: {e}")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return jsonify({"mensaje": "Error interno", "error": str(e)}), 500
        
    finally:
        db.close()