from flask import Flask, request, jsonify, current_app
from flask_cors import CORS
from logica import reservas
from logica.auth import auth_bp
from sqlalchemy import text
from logica.negocios import obtener_tipo_negocio_por_tenant
from config.bd import engine, Base
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_jwt
from functools import wraps
from logica.reservas.factory import *
from logica.decoradores import *
from logica.admin.lugares_admin import actualizar_lugar_admin, eliminar_lugar_admin, listar_lugares_admin
from logica.admin.admin_factory import obtener_admin_handler
import traceback # Importa traceback
from init_db import inicializar_base_de_datos
import os

app = Flask(__name__)

origins = [
    "http://localhost:3000",
    "https://reservas.systempiura.com",
    "http://reservas.systempiura.com"
]
CORS(app, origins=origins, supports_credentials=True)

# JWT Configuración
app.config['JWT_SECRET_KEY'] = 'supersecreto'
jwt = JWTManager(app)

# Inicializar tablas
#Base.metadata.create_all(bind=engine)

# =========================================================================
# MANTENIENDO TU PATRÓN DE CONEXIÓN GLOBAL
# =========================================================================
with app.app_context():
    # 1. Llama a tu script de inicialización
    if os.getenv("RUN_INIT_DB", "true").lower() == "true":
         inicializar_base_de_datos()
    
    # 2. Establece tu conexión global que usa el resto de la app
    print("Estableciendo conexión de BD global para la app Flask...")
    current_app.db = engine.connect()
    current_app.db.commit() # Limpia la transacción
    print("✅ Conexión de BD global lista.")


#==========================login ================================================
# Registrar blueprint
app.register_blueprint(auth_bp)

# Decorador para proteger rutas de admin
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        # Asumiendo 2 = admin
        if claims.get("rol_id") != 2: 
            return jsonify({"error": "Acceso denegado: solo administradores"}), 403
        return fn(*args, **kwargs)
    return wrapper


@app.errorhandler(Exception)
def handle_exception(e):
    # Manejador de errores global
    # Intenta hacer rollback en la conexión compartida
    try:
        current_app.db.rollback()
    except Exception as rb_e:
        print(f"Error durante el rollback en el manejador de errores: {rb_e}")
        
    traceback.print_exc()
    # Devuelve un error genérico
    return jsonify({"error": f"Error interno del servidor: {str(e)}"}), 500

## RUTA REFACTORIZADA ##
@app.route('/api/usuario/info', methods=['GET'])
@jwt_required()
def obtener_info_usuario():
    try:
        usuario_id = get_jwt_identity()
        query = text("SELECT id, nombre, correo, rol_id, tenant_id FROM usuarios WHERE id = :usuario_id")
        result = current_app.db.execute(query, {"usuario_id": usuario_id}).fetchone()
        
        # Hacemos commit para cerrar la transacción de este SELECT
        current_app.db.commit() 
        
        if result:
            return jsonify(dict(result._mapping))
        else:
            return jsonify({"error": "Sesión inválida. Usuario no encontrado."}), 401
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error en base de datos: {str(e)}"}), 500

#============================ hacer reservas =================================================================

## RUTA REFACTORIZADA ##
@app.route('/api/reservas', methods=['POST'])
@jwt_required()
@extraer_identidad
def hacer_reserva(identidad):
    try:
        datos = request.json
        tenant_id = identidad["tenant_id"]
        usuario_id = identidad["usuario_id"]

        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
        if not tipo_negocio:
            return jsonify({"error": "No se pudo obtener el tipo de negocio. Verifica los datos."}), 400

        handler = obtener_reserva_handler(tipo_negocio, db=current_app.db, tenant_id=tenant_id)

        datos['usuario_id'] = usuario_id
        datos['tenant_id'] = tenant_id 
        print(">>> Datos finales para crear reserva:", datos)
        resultado = handler.crear_reserva(datos)
        # Asumiendo que crear_reserva hace commit/rollback
        return jsonify(resultado)
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al crear reserva: {str(e)}"}), 500

#==============================listar reservas ============================================================

## RUTA REFACTORIZADA ##
@app.route('/api/reservas', methods=['GET'])
@jwt_required()
@extraer_identidad
def listar_reservas(identidad):
    try:
        tenant_id = identidad["tenant_id"]
        usuario_id = identidad["usuario_id"] # <-- Aquí tienes el ID
        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
        handler = obtener_reserva_handler(tipo_negocio, db=current_app.db, tenant_id=tenant_id)
        
        # --- CAMBIO AQUÍ ---
        # Ya no necesitamos el 'if hasattr'.
        # Pasamos el usuario_id directamente como argumento.
        reservas = handler.listar_reservas(usuario_id=usuario_id)
        
        current_app.db.commit() # <-- Cierra la transacción
        return jsonify(reservas)
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al listar reservas: {str(e)}"}), 500

## RUTA REFACTORIZADA ##
@app.route('/api/admin/lugares', methods=['GET'])
@admin_required
def listar_lugares_admin_route():
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")
        resultado = listar_lugares_admin(tenant_id) # Asumiendo que esta usa current_app.db
        current_app.db.commit() # <-- Cierra la transacción
        return jsonify(resultado)
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al listar lugares: {str(e)}"}), 500

#------------------------------- ver disponibilidad de cupos -------------------------------------------------------

## RUTA REFACTORIZADA ##
@app.route('/api/disponibilidad', methods=['GET'])
@jwt_required()
@extraer_identidad
def consultar_disponibilidad(identidad):
    try:
        tenant_id = identidad.get("tenant_id")
        fecha_inicio = request.args.get('inicio')
        fecha_fin = request.args.get('fin')

        if not fecha_inicio or not fecha_fin:
            return jsonify({"error": "Debes proporcionar 'inicio' y 'fin'"}), 400

        # Validar formato de fecha
        from datetime import datetime
        datetime.strptime(fecha_inicio, '%Y-%m-%d')
        datetime.strptime(fecha_fin, '%Y-%m-%d')
            
        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id) # Esta fue la que falló
        
        handler = obtener_reserva_handler(tipo_negocio, db=current_app.db, tenant_id=tenant_id)
        disponibilidad = handler.consultar_disponibilidad_por_dias(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        current_app.db.commit() # <-- Cierra la transacción
        return jsonify(disponibilidad)
        
    except ValueError:
        # Este error es por formato de fecha, no de BD, no necesita rollback
        return jsonify({"error": "Formato de fecha inválido. Usa 'YYYY-MM-DD'"}), 400
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al consultar disponibilidad: {str(e)}"}), 500


#==============FUNCIONES ADMINISTRADOR ====================================

## RUTA REFACTORIZADA ##
@app.route('/api/admin/reservas', methods=['GET'])
@admin_required
def listar_reservas_admin_route():
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")
        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
        
        print("solucionando el link")
        print("🧪 Tipo de negocio:", tipo_negocio)
        
        handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
        reservas = handler.listar_reserva()
        current_app.db.commit() # <-- Cierra la transacción
        return jsonify(reservas)
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al listar reservas de admin: {str(e)}"}), 500

## RUTA REFACTORIZADA ##
@app.route('/api/admin/reservas', methods=['POST'])
@admin_required
def crear_reserva_admin():
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")
        datos = request.json

        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
        handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
        datos['tenant_id'] = tenant_id
        if 'usuario_id' not in datos:
            datos['usuario_id'] = identidad.get("usuario_id") 
        
        # Asumiendo que handler.crear_reserva hace commit/rollback
        respuesta, status = handler.crear_reserva(datos)
        return jsonify(respuesta), status
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al crear reserva de admin: {str(e)}"}), 500

## RUTA REFACTORIZADA ##
@app.route('/api/admin/reservas/<int:reserva_id>', methods=['PUT'])
@admin_required
def editar_reserva_admin(reserva_id):
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")
        datos = request.json

        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
        handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
        # Asumiendo que handler.editar_reserva hace commit/rollback
        return jsonify(handler.editar_reserva(reserva_id, datos))
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al editar reserva: {str(e)}"}), 500

## RUTA REFACTORIZADA ##
@app.route('/api/admin/reservas/<int:reserva_id>', methods=['DELETE'])
@admin_required
def eliminar_reserva_admin(reserva_id):
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")

        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
        handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
        # Asumiendo que handler.eliminar_reserva hace commit/rollback
        return jsonify(handler.eliminar_reserva(reserva_id))
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al eliminar reserva: {str(e)}"}), 500

## RUTA REFACTORIZADA ##
@app.route('/api/admin/lugares/<int:lugar_id>', methods=['PUT'])
@admin_required
def editar_lugar_admin(lugar_id):
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")
        datos = request.json

        resultado = actualizar_lugar_admin(tenant_id, lugar_id, datos)
        # Asumiendo que actualizar_lugar_admin hace commit/rollback
        return jsonify(resultado)
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al editar lugar: {str(e)}"}), 500

## RUTA REFACTORIZADA ##
@app.route('/api/admin/lugares/<int:lugar_id>', methods=['DELETE'])
@admin_required
def eliminar_lugar_admin_route(lugar_id):
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")

        resultado = eliminar_lugar_admin(tenant_id, lugar_id)
        # Asumiendo que eliminar_lugar_admin hace commit/rollback
        return jsonify(resultado)
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIAN!
        traceback.print_exc()
        return jsonify({"error": f"Error al eliminar lugar: {str(e)}"}), 500

#========================CIERRE DE FUNCIONES ADMIN======================

# ESTA RUTA YA ESTABA CORRECTA (TENÍA TRY/EXCEPT)
@app.route('/api/admin/lugares', methods=['POST'])
@admin_required
def crear_lugar():
    datos = request.json
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    
    if not tenant_id:
        return jsonify({"error": "No se pudo obtener el tenant_id"}), 400
    
    try:
        # Obtener el tipo de negocio del tenant
        tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
        if not tipo_negocio:
            return jsonify({"error": "No se pudo obtener el tipo de negocio"}), 400
            
        datos['tenant_id'] = tenant_id
        datos['tipo'] = tipo_negocio
        
        # Validate required fields
        required_fields = ['nombre', 'capacidad', 'zona']
        for field in required_fields:
            if not datos.get(field):
                return jsonify({"error": f"El campo {field} es requerido"}), 400
            
        query = text("""
            INSERT INTO lugares (nombre, capacidad, tenant_id, tipo, zona) 
            VALUES (:nombre, :capacidad, :tenant_id, :tipo, :zona)
            RETURNING id
        """)
        result = current_app.db.execute(query, datos)
        current_app.db.commit() # <-- Correcto
        
        lugar_id = result.fetchone()[0]
        return jsonify({
            "mensaje": "Lugar creado exitosamente",
            "id": lugar_id
        }), 201
        
    except Exception as e:
        current_app.db.rollback() # <-- Correcto
        traceback.print_exc()
        return jsonify({"error": f"Error al crear lugar: {str(e)}"}), 500


## RUTA REFACTORIZADA ##
@app.route('/api/admin/usuarios', methods=['GET'])
@admin_required
def listar_usuarios_mismo_tenant():
    try:
        identidad = get_jwt()
        tenant_id = identidad.get("tenant_id")
        query = text("SELECT id, nombre, correo FROM usuarios WHERE tenant_id = :tenant_id AND rol_id = 1")
        result = current_app.db.execute(query, {"tenant_id": tenant_id})
        
        usuarios = [dict(row._mapping) for row in result]
        current_app.db.commit() # <-- Cierra la transacción
        
        return jsonify(usuarios)
    except Exception as e:
        current_app.db.rollback() # <-- ¡LA SOLUCIÓN!
        traceback.print_exc()
        return jsonify({"error": f"Error al listar usuarios: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)