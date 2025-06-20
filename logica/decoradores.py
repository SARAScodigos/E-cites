from flask_jwt_extended import get_jwt, get_jwt_identity
from functools import wraps

def extraer_identidad(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        identidad = {
            "usuario_id": get_jwt_identity(),
            "tenant_id": get_jwt().get("tenant_id"),
            "rol_id": get_jwt().get("rol_id"),
        }
        return func(*args, identidad=identidad, **kwargs)
    return wrapper