from flask import Flask, request, jsonify
from flask_cors import CORS
from logica import reservas
from logica.auth import auth_bp
from sqlalchemy import text
from logica.negocios import obtener_tipo_negocio_por_tenant
from config.bd import engine, Base
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_jwt_extended import get_jwt_identity, get_jwt
from functools import wraps
from logica.reservas.factory import *
from logica.decoradores import *
from logica.admin.lugares_admin import actualizar_lugar_admin, eliminar_lugar_admin, listar_lugares_admin
from flask import current_app
from logica.admin.admin_factory import obtener_admin_handler

app = Flask(__name__)
CORS(app)

# JWT Configuración
app.config['JWT_SECRET_KEY'] = 'supersecreto'  # ¡Cámbialo por uno fuerte!
jwt = JWTManager(app)

# Inicializar tablas (si es necesario)
Base.metadata.create_all(bind=engine)
with app.app_context():
    current_app.db = engine.connect()

#==========================login ================================================
# Registrar blueprint
app.register_blueprint(auth_bp)

# Decorador para proteger rutas de admin
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()  # ✅ aquí están los datos adicionales
        if claims.get("rol_id") != 2:
            return jsonify({"error": "Acceso denegado: solo administradores"}), 403
        return fn(*args, **kwargs)
    return wrapper


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    traceback.print_exc()  # Esto imprime el error completo en la consola
    return jsonify({"error": str(e)}), 500

@app.route('/api/usuario/info', methods=['GET'])
@jwt_required()
def obtener_info_usuario():
    usuario_id = get_jwt_identity()  # Esto será el ID (str o int)
    query = text("SELECT id, nombre, correo, rol_id, tenant_id FROM usuarios WHERE id = :usuario_id")
    result = current_app.db.execute(query, {"usuario_id": usuario_id}).fetchone()
    if result:
        return jsonify(dict(result._mapping))
    else:
        return jsonify({"error": "Sesión inválida. Usuario no encontrado."}), 401

#============================ hacer reservas =================================================================

@app.route('/api/reservas', methods=['POST'])
@jwt_required()
@extraer_identidad
def hacer_reserva(identidad):
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
    return jsonify(resultado)

#==============================listar reservas ============================================================


@app.route('/api/reservas', methods=['GET'])
@jwt_required()
@extraer_identidad
def listar_reservas(identidad):
    tenant_id = identidad["tenant_id"]
    usuario_id = identidad["usuario_id"]  # Obtener el usuario actual
    tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
    handler = obtener_reserva_handler(tipo_negocio, db=current_app.db, tenant_id=tenant_id)
    
    # Si el handler necesita el usuario_id, agregarlo
    if hasattr(handler, 'usuario_id'):
        handler.usuario_id = usuario_id
    
    return jsonify(handler.listar_reservas())

@app.route('/api/admin/lugares', methods=['GET'])
@admin_required
def listar_lugares_admin_route():
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    resultado = listar_lugares_admin(tenant_id)
    return jsonify(resultado)
#------------------------------- ver disponibilidad de cupos -------------------------------------------------------


@app.route('/api/disponibilidad', methods=['GET'])
@jwt_required()
@extraer_identidad
def consultar_disponibilidad(identidad):
    tenant_id = identidad.get("tenant_id")
    fecha_inicio = request.args.get('inicio')  # Ej: ?inicio=2025-06-14
    fecha_fin = request.args.get('fin')        # Ej: &fin=2025-06-18
    tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)

    if not fecha_inicio or not fecha_fin:
        return jsonify({"error": "Debes proporcionar 'inicio' y 'fin'"}), 400

    try:
        # Validar formato de fecha
        from datetime import datetime
        datetime.strptime(fecha_inicio, '%Y-%m-%d')
        datetime.strptime(fecha_fin, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido. Usa 'YYYY-MM-DD'"}), 400

    try:
        handler = obtener_reserva_handler(tipo_negocio, db=current_app.db, tenant_id=tenant_id)
        disponibilidad = handler.consultar_disponibilidad_por_dias(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        return jsonify(disponibilidad)
    except Exception as e:
        return jsonify({"error": f"Error al consultar disponibilidad: {str(e)}"}), 500


# Ejemplo de ruta solo para administradores
#==============FUNCIONES ADMINISTRADOR ====================================
@app.route('/api/admin/reservas', methods=['GET'])
@admin_required
def listar_reservas_admin_route():
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
    print("solucioando el link")
    print("🧪 Tipo de negocio:", tipo_negocio)
    handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
    return jsonify(handler.listar_reserva())

@app.route('/api/admin/reservas', methods=['POST'])
@admin_required
def crear_reserva_admin():
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    datos = request.json

    tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
    handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
    datos['tenant_id'] = tenant_id
    if 'usuario_id' not in datos:
        datos['usuario_id'] = identidad.get("usuario_id") 
    
    
    respuesta, status = handler.crear_reserva(datos)
    return jsonify(respuesta), status

@app.route('/api/admin/reservas/<int:reserva_id>', methods=['PUT'])
@admin_required
def editar_reserva_admin(reserva_id):
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    datos = request.json

    tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
    handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
    return jsonify(handler.editar_reserva(reserva_id, datos))

@app.route('/api/admin/reservas/<int:reserva_id>', methods=['DELETE'])
@admin_required
def eliminar_reserva_admin(reserva_id):
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")

    tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
    handler = obtener_admin_handler(tipo_negocio, current_app.db, tenant_id)
    return jsonify(handler.eliminar_reserva(reserva_id))

@app.route('/api/admin/lugares/<int:lugar_id>', methods=['PUT'])
@admin_required
def editar_lugar_admin(lugar_id):
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    datos = request.json

    resultado = actualizar_lugar_admin(tenant_id, lugar_id, datos)
    return jsonify(resultado)

@app.route('/api/admin/lugares/<int:lugar_id>', methods=['DELETE'])
@admin_required
def eliminar_lugar_admin_route(lugar_id):
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")

    resultado = eliminar_lugar_admin(tenant_id, lugar_id)
    return jsonify(resultado)

#========================CIERRE DE FUNCIONES ADMIN======================

@app.route('/api/admin/lugares', methods=['POST'])
@admin_required
def crear_lugar():
    datos = request.json
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    
    if not tenant_id:
        return jsonify({"error": "No se pudo obtener el tenant_id"}), 400
    
    # Obtener el tipo de negocio del tenant
    tipo_negocio = obtener_tipo_negocio_por_tenant(tenant_id)
    if not tipo_negocio:
        return jsonify({"error": "No se pudo obtener el tipo de negocio"}), 400
        
    datos['tenant_id'] = tenant_id
    datos['tipo'] = tipo_negocio
    
    try:
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
        current_app.db.commit()
        
        lugar_id = result.fetchone()[0]
        return jsonify({
            "mensaje": "Lugar creado exitosamente",
            "id": lugar_id
        }), 201
        
    except Exception as e:
        current_app.db.rollback()
        return jsonify({"error": f"Error al crear lugar: {str(e)}"}), 500


@app.route('/api/admin/usuarios', methods=['GET'])
@admin_required
def listar_usuarios_mismo_tenant():
    identidad = get_jwt()
    tenant_id = identidad.get("tenant_id")
    query = text("SELECT id, nombre, correo FROM usuarios WHERE tenant_id = :tenant_id AND rol_id = 1")
    result = current_app.db.execute(query, {"tenant_id": tenant_id})
    return jsonify([dict(row._mapping) for row in result])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
