from sqlalchemy import text
from flask import current_app

def obtener_tipo_negocio_por_tenant(tenant_id):
    try:
        query = text("SELECT tipo FROM negocios WHERE id = :id")
        result = current_app.db.execute(query, {"id": tenant_id}).fetchone()
        return result[0] if result else None
    except Exception as e:
        print("❌ Error al obtener tipo de negocio:", e)
        current_app.db.rollback()  # muy importante
        return None