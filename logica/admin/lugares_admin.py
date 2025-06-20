from sqlalchemy import text
from flask import current_app

def actualizar_lugar_admin(tenant_id, lugar_id, datos):
    # Solo campos permitidos
    campos_editables = ["nombre", "descripcion", "capacidad", "tipo", "zona", "activo"]

    set_clauses = []
    valores = {"lugar_id": lugar_id, "tenant_id": tenant_id}

    for campo in campos_editables:
        if campo in datos:
            set_clauses.append(f"{campo} = :{campo}")
            valores[campo] = datos[campo]

    if not set_clauses:
        return {"error": "No se proporcionaron campos válidos para actualizar"}, 400

    sql = f"""
        UPDATE lugares
        SET {', '.join(set_clauses)}
        WHERE id = :lugar_id AND tenant_id = :tenant_id
        RETURNING id
    """

    try:
        result = current_app.db.execute(text(sql), valores)
        if result.rowcount == 0:
            return {"error": "Lugar no encontrado o no pertenece al negocio"}, 404
        current_app.db.commit()
        return {"mensaje": "Lugar actualizado correctamente"}
    except Exception as e:
        current_app.db.rollback()
        return {"error": str(e)}, 500

def eliminar_lugar_admin(tenant_id, lugar_id):
    try:
        query = text("""
            UPDATE lugares
            SET activo = FALSE
            WHERE id = :lugar_id AND tenant_id = :tenant_id
            RETURNING id
        """)
        result = current_app.db.execute(query, {
            "lugar_id": lugar_id,
            "tenant_id": tenant_id
        })
        if result.rowcount == 0:
            return {"error": "Lugar no encontrado o no pertenece al negocio"}, 404

        current_app.db.commit()
        return {"mensaje": "Lugar desactivado correctamente"}

    except Exception as e:
        current_app.db.rollback()
        return {"error": str(e)}, 500

def listar_lugares_admin(tenant_id):
    try:
        query = text("""
            SELECT id, nombre, descripcion, capacidad, tipo, zona, activo
            FROM lugares
            WHERE tenant_id = :tenant_id
            ORDER BY nombre
        """)
        result = current_app.db.execute(query, {"tenant_id": tenant_id})
        return [dict(row._mapping) for row in result]
    except Exception as e:
        return {"error": str(e)}, 500