from flask_jwt_extended import create_access_token

def autenticar_usuario(nombre, clave):
    # (Tu lógica de autenticación actual aquí...)

    if resultado:
        usuario = dict(resultado)
        access_token = create_access_token(identity={
            'id': usuario['id'],
            'rol_id': usuario['rol_id'],
            'tenant_id': usuario['tenant_id']
        })
        return {
            "success": True,
            "message": "Autenticación exitosa",
            "access_token": access_token
        }
    else:
        return {
            "success": False,
            "message": "Credenciales incorrectas"
        }
