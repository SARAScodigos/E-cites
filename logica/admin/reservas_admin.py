from sqlalchemy import text
from flask import current_app



def crear_reserva_admin_muelle(tenant_id, datos):
    requeridos = ["usuario_id", "lugar_id", "fecha", "fecha_entrada", "fecha_salida", "tipo_embarcacion"]
    for campo in requeridos:
        if campo not in datos:
            return {"error": f"Falta el campo obligatorio: {campo}"}, 400

    datos["tenant_id"] = tenant_id  # Se fuerza el tenant

    try:
        # Verificar si el lugar pertenece al negocio
        lugar = current_app.db.execute(text("""
            SELECT capacidad FROM lugares
            WHERE id = :lugar_id AND tenant_id = :tenant_id
        """), {"lugar_id": datos["lugar_id"], "tenant_id": tenant_id}).fetchone()

        if not lugar:
            return {"error": "Lugar no válido o no pertenece al negocio"}, 403

        capacidad = lugar[0]

        # Validar disponibilidad (reservas solapadas)
        query_ocupadas = text("""
            SELECT COUNT(*) FROM reservas_generales rg
            JOIN reservas_muelle rm ON rg.id = rm.reserva_id
            WHERE rg.lugar_id = :lugar_id
              AND rg.tenant_id = :tenant_id
              AND daterange(rm.fecha_entrada, rm.fecha_salida, '[]') &&
                  daterange(:fecha_entrada, :fecha_salida, '[]')
        """)
        ocupadas = current_app.db.execute(query_ocupadas, {
            "lugar_id": datos["lugar_id"],
            "tenant_id": tenant_id,
            "fecha_entrada": datos["fecha_entrada"],
            "fecha_salida": datos["fecha_salida"]
        }).scalar()

        if ocupadas >= capacidad:
            return {"error": "No hay espacios disponibles en ese rango de fechas"}, 409

        # Insertar en reservas_generales
        query_general = text("""
            INSERT INTO reservas_generales (usuario_id, tenant_id, lugar_id, fecha)
            VALUES (:usuario_id, :tenant_id, :lugar_id, :fecha)
            RETURNING id
        """)
        result = current_app.db.execute(query_general, datos)
        reserva_id = result.fetchone()[0]

        # Insertar en reservas_muelle
        query_muelle = text("""
            INSERT INTO reservas_muelle (
                reserva_id, fecha_entrada, fecha_salida, tipo_embarcacion,
                requiere_pintura, requiere_mecanica, requiere_motor
            ) VALUES (
                :reserva_id, :fecha_entrada, :fecha_salida, :tipo_embarcacion,
                :requiere_pintura, :requiere_mecanica, :requiere_motor
            )
        """)
        current_app.db.execute(query_muelle, {
            "reserva_id": reserva_id,
            "fecha_entrada": datos["fecha_entrada"],
            "fecha_salida": datos["fecha_salida"],
            "tipo_embarcacion": datos["tipo_embarcacion"],
            "requiere_pintura": datos.get("requiere_pintura", False),
            "requiere_mecanica": datos.get("requiere_mecanica", False),
            "requiere_motor": datos.get("requiere_motor", False)
        })

        current_app.db.commit()
        return {"mensaje": "Reserva creada por el administrador", "reserva_id": reserva_id}, 201

    except Exception as e:
        current_app.db.rollback()
        return {"error": str(e)}, 500
    
def editar_reserva_admin_muelle(tenant_id, reserva_id, datos):
    try:
        # Validar que la reserva pertenezca al negocio
        query_validar = text("""
            SELECT rg.lugar_id FROM reservas_generales rg
            WHERE rg.id = :reserva_id AND rg.tenant_id = :tenant_id
        """)
        lugar_row = current_app.db.execute(query_validar, {
            "reserva_id": reserva_id,
            "tenant_id": tenant_id
        }).fetchone()

        if not lugar_row:
            return {"error": "Reserva no encontrada o no pertenece al negocio"}, 404

        lugar_id = lugar_row[0]

        # Validar que el lugar siga teniendo disponibilidad en las nuevas fechas
        if "fecha_entrada" in datos and "fecha_salida" in datos:
            query_lugar = text("""
                SELECT capacidad FROM lugares WHERE id = :lugar_id AND tenant_id = :tenant_id
            """)
            capacidad = current_app.db.execute(query_lugar, {
                "lugar_id": lugar_id,
                "tenant_id": tenant_id
            }).scalar()

            query_conflicto = text("""
                SELECT COUNT(*) FROM reservas_generales rg
                JOIN reservas_muelle rm ON rg.id = rm.reserva_id
                WHERE rg.lugar_id = :lugar_id
                  AND rg.tenant_id = :tenant_id
                  AND rg.id != :reserva_id
                  AND daterange(rm.fecha_entrada, rm.fecha_salida, '[]') &&
                      daterange(:fecha_entrada, :fecha_salida, '[]')
            """)
            ocupadas = current_app.db.execute(query_conflicto, {
                "lugar_id": lugar_id,
                "tenant_id": tenant_id,
                "reserva_id": reserva_id,
                "fecha_entrada": datos["fecha_entrada"],
                "fecha_salida": datos["fecha_salida"]
            }).scalar()

            if ocupadas >= capacidad:
                return {"error": "No hay disponibilidad en ese rango de fechas"}, 409

        # Actualizar campos en reservas_muelle
        campos_editables = ["fecha_entrada", "fecha_salida", "tipo_embarcacion",
                            "requiere_pintura", "requiere_mecanica", "requiere_motor"]
        set_clauses = []
        valores = {"reserva_id": reserva_id}

        for campo in campos_editables:
            if campo in datos:
                set_clauses.append(f"{campo} = :{campo}")
                valores[campo] = datos[campo]

        if not set_clauses:
            return {"error": "No se proporcionaron campos válidos para actualizar"}, 400

        sql = f"""
            UPDATE reservas_muelle
            SET {', '.join(set_clauses)}
            WHERE reserva_id = :reserva_id
        """
        current_app.db.execute(text(sql), valores)
        current_app.db.commit()

        return {"mensaje": "Reserva actualizada correctamente"}

    except Exception as e:
        current_app.db.rollback()
        return {"error": str(e)}, 500