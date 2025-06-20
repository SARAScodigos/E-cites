from flask import Blueprint, request, jsonify
from config.bd import SessionLocal
from modelos.usuario_model import Usuario
from modelos.negocio_model import Negocio
from sqlalchemy import text
import bcrypt
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/api/registro", methods=["POST"])
@jwt_required()

def registro():
    identidad = get_jwt_identity()  # esto solo será el ID del usuario
    claims = get_jwt()              # aquí están tenant_id y rol_id

    if claims['rol_id'] != 2:
        return jsonify({"mensaje": "Solo administradores pueden registrar usuarios"}), 403

    datos = request.get_json()
    nombre = datos.get("nombre")
    correo = datos.get("correo")
    clave = datos.get("clave")

    if not nombre or not correo or not clave:
        return jsonify({"mensaje": "Faltan datos"}), 400

    db = SessionLocal()
    try:
        existe = db.query(Usuario).filter_by(correo=correo).first()
        if existe:
            return jsonify({"mensaje": "El correo ya está registrado"}), 409

        hashed_pw = bcrypt.hashpw(clave.encode("utf-8"), bcrypt.gensalt())

        nuevo_usuario = Usuario(
            nombre=nombre,
            correo=correo,
            clave=hashed_pw.decode("utf-8"),
            rol_id=1,  # usuario normal
            tenant_id=claims['tenant_id']  # ✅ del token del admin
        )
        db.add(nuevo_usuario)
        db.commit()
        return jsonify({"mensaje": "Usuario registrado exitosamente"})

    except Exception as e:
        db.rollback()
        return jsonify({"mensaje": "Error interno", "error": str(e)}), 500
    finally:
        db.close()

@auth_bp.route("/api/login", methods=["POST"])
def login():
    datos = request.get_json()
    correo = datos.get("correo")
    clave = datos.get("clave")

    if not correo or not clave:
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
            return jsonify({"mensaje": "Login exitoso", "access_token": access_token})
        else:
            return jsonify({"mensaje": "Credenciales incorrectas"}), 401
    finally:
        db.close()
