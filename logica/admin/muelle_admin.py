# logica/admin/muelle_admin.py

from .base_admin import AdminReservaBase
from sqlalchemy import text
from flask import current_app
from datetime import datetime

class AdminReservaMuelle(AdminReservaBase):
    
    def editar_reserva(self, reserva_id, datos):
        try:
            # Validar que la reserva pertenezca al negocio
            query_validar = text("""
                SELECT rg.lugar_id FROM reservas_generales rg
                WHERE rg.id = :reserva_id AND rg.tenant_id = :tenant_id
            """)
            lugar_row = current_app.db.execute(query_validar, {
                "reserva_id": reserva_id,
                "tenant_id": self.tenant_id
            }).fetchone()
    
            if not lugar_row:
                return {"error": "Reserva no encontrada o no pertenece al negocio"}, 404
    
            lugar_id = datos.get("lugar_id", lugar_row[0])
    
            # Validar que el lugar siga teniendo disponibilidad en las nuevas fechas
            if "fecha_entrada" in datos and "fecha_salida" in datos:
                query_lugar = text("""
                    SELECT capacidad FROM lugares WHERE id = :lugar_id AND tenant_id = :tenant_id
                """)
                capacidad = current_app.db.execute(query_lugar, {
                    "lugar_id": lugar_id,
                    "tenant_id": self.tenant_id
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
                    "tenant_id": self.tenant_id,
                    "reserva_id": reserva_id,
                    "fecha_entrada": datos["fecha_entrada"],
                    "fecha_salida": datos["fecha_salida"]
                }).scalar()
    
                if ocupadas >= capacidad:
                    return {"error": "No hay disponibilidad en ese rango de fechas"}, 409
                        # 🛠️ Actualizar reservas_generales si hay cambios
            update_generales = []
            valores_generales = {
                "reserva_id": reserva_id,
                "tenant_id": self.tenant_id
            }

            if "fecha" in datos:
                update_generales.append("fecha = :fecha")
                valores_generales["fecha"] = datos["fecha"]

            if "lugar_id" in datos:
                update_generales.append("lugar_id = :lugar_id")
                valores_generales["lugar_id"] = datos["lugar_id"]

            if "usuario_id" in datos:
                update_generales.append("usuario_id = :usuario_id")
                valores_generales["usuario_id"] = datos["usuario_id"]

            if update_generales:
                sql_general = f"""
                    UPDATE reservas_generales
                    SET {', '.join(update_generales)}
                    WHERE id = :reserva_id AND tenant_id = :tenant_id
                """
                current_app.db.execute(text(sql_general), valores_generales)    


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
    
    def crear_reserva(self, datos):
        requeridos = ["usuario_id", "lugar_id", "fecha_entrada", "fecha_salida", "tipo_embarcacion"]
        
        print("📥 Datos recibidos:", datos)

        for campo in requeridos:
            if campo not in datos:
                print(f"❌ FALTA: {campo}")
                return {"error": f"Falta el campo obligatorio: {campo}"}, 400
    
        try:
            # 🔐 Forzar tenant_id desde el token (no confiar en lo que venga en JSON)
            datos["tenant_id"] = self.tenant_id
    
            # 🗓️ Convertir fechas desde string a date
            datos["fecha_entrada"] = datetime.strptime(datos["fecha_entrada"], "%Y-%m-%d").date()
            datos["fecha_salida"] = datetime.strptime(datos["fecha_salida"], "%Y-%m-%d").date()
            datos["fecha"] = datetime.now().date()
    
            # ⚠ Validación de coherencia temporal
            hoy = datetime.now().date()
            if datos["fecha_entrada"] < hoy:
                return {"error": "No se puede reservar en fechas anteriores a hoy"}, 400
            if datos["fecha_salida"] < datos["fecha_entrada"]:
                return {"error": "La fecha de salida no puede ser anterior a la fecha de entrada"}, 400
    
            # 👤 Validar que el usuario exista y pertenezca al negocio
            usuario = current_app.db.execute(text("""
                SELECT id FROM usuarios
                WHERE id = :usuario_id AND tenant_id = :tenant_id
            """), {
                "usuario_id": datos["usuario_id"],
                "tenant_id": self.tenant_id
            }).fetchone()
    
            if not usuario:
                return {"error": "Usuario no válido o no pertenece al negocio"}, 403
    
            # 📍 Validar que el lugar existe y pertenece al negocio
            lugar = current_app.db.execute(text("""
                SELECT capacidad FROM lugares
                WHERE id = :lugar_id AND tenant_id = :tenant_id
            """), {
                "lugar_id": datos["lugar_id"],
                "tenant_id": self.tenant_id
            }).fetchone()
    
            if not lugar:
                return {"error": "Lugar no válido o no pertenece al negocio"}, 403
    
            capacidad = lugar[0]
            '''
            # 🚫 Validar solapamiento de reservas del usuario
            conflicto_usuario = current_app.db.execute(text("""
                SELECT 1 FROM reservas_generales rg
                JOIN reservas_muelle rm ON rg.id = rm.reserva_id
                WHERE rg.usuario_id = :usuario_id
                  AND rg.lugar_id = :lugar_id
                  AND rg.tenant_id = :tenant_id
                  AND daterange(rm.fecha_entrada, rm.fecha_salida, '[]') &&
                      daterange(:fecha_entrada, :fecha_salida, '[]')
                LIMIT 1
            """), {
                "usuario_id": datos["usuario_id"],
                "lugar_id": datos["lugar_id"],
                "tenant_id": self.tenant_id,
                "fecha_entrada": datos["fecha_entrada"],
                "fecha_salida": datos["fecha_salida"]
            }).fetchone()
    
            if conflicto_usuario:
                return {"error": "Este usuario ya tiene una reserva en ese horario"}, 409
            '''
            # 🧮 Validar si hay cupos disponibles en el lugar para ese rango de fechas
            # 🧮 Validar si hay al menos un día con la capacidad ocupada
            query_cupo_dia = text("""
            WITH dias_nuevos AS (
              SELECT generate_series(:fecha_entrada, :fecha_salida, interval '1 day') AS dia
            ),
            ocupacion_por_dia AS (
              SELECT d.dia, COUNT(*) AS ocupadas
              FROM dias_nuevos d
              JOIN reservas_muelle rm ON d.dia BETWEEN rm.fecha_entrada::date AND rm.fecha_salida::date
              JOIN reservas_generales rg ON rm.reserva_id = rg.id
              WHERE rg.lugar_id = :lugar_id AND rg.tenant_id = :tenant_id
              GROUP BY d.dia
            )
            SELECT d.dia, ocupadas FROM ocupacion_por_dia d ORDER BY d.dia
            """)
            dias = current_app.db.execute(query_cupo_dia, {
                "fecha_entrada": datos["fecha_entrada"],
                "fecha_salida": datos["fecha_salida"],
                "lugar_id": datos["lugar_id"],
                "tenant_id": self.tenant_id
            }).fetchall()

            print("📊 Ocupación diaria del lugar:")
            for dia in dias:
                print(f"🗓️ {dia.dia} → {dia.ocupadas} reservas")

            ocupacion_maxima = max([d.ocupadas for d in dias], default=0)
            if ocupacion_maxima >= capacidad:
                return {"error": "No hay espacios disponibles en alguno de los días"}, 409

    
            # ✅ Insertar en reservas_generales
            result = current_app.db.execute(text("""
                INSERT INTO reservas_generales (usuario_id, tenant_id, lugar_id, fecha)
                VALUES (:usuario_id, :tenant_id, :lugar_id, :fecha)
                RETURNING id
            """), datos)
            reserva_id = result.fetchone()[0]
    
            # ✅ Insertar en reservas_muelle
            current_app.db.execute(text("""
                INSERT INTO reservas_muelle (
                    reserva_id, fecha_entrada, fecha_salida, tipo_embarcacion,
                    requiere_pintura, requiere_mecanica, requiere_motor
                ) VALUES (
                    :reserva_id, :fecha_entrada, :fecha_salida, :tipo_embarcacion,
                    :requiere_pintura, :requiere_mecanica, :requiere_motor
                )
            """), {
                "reserva_id": reserva_id,
                "fecha_entrada": datos["fecha_entrada"],
                "fecha_salida": datos["fecha_salida"],
                "tipo_embarcacion": datos["tipo_embarcacion"],
                "requiere_pintura": datos.get("requiere_pintura", False),
                "requiere_mecanica": datos.get("requiere_mecanica", False),
                "requiere_motor": datos.get("requiere_motor", False)
            })
    
            current_app.db.commit()
            return {"mensaje": "Reserva creada exitosamente", "reserva_id": reserva_id}, 201
    
        except Exception as e:
            current_app.db.rollback()
            return {"error": str(e)}, 500
    
        

    
    def listar_reserva(self):
        try:
            query = text("""
                SELECT rg.id AS reserva_id,
                       rg.fecha,
                       rg.usuario_id,
                       rg.lugar_id,
                       TO_CHAR(rm.fecha_entrada, 'YYYY-MM-DD') AS fecha_entrada,
                       TO_CHAR(rm.fecha_salida, 'YYYY-MM-DD') AS fecha_salida,
                       rm.tipo_embarcacion,
                       rm.requiere_pintura,
                       rm.requiere_mecanica,
                       rm.requiere_motor,
                       u.nombre AS usuario,
                       l.nombre AS lugar
                FROM reservas_generales rg
                JOIN reservas_muelle rm ON rg.id = rm.reserva_id
                JOIN usuarios u ON rg.usuario_id = u.id
                JOIN lugares l ON rg.lugar_id = l.id
                WHERE rg.tenant_id = :tenant_id
                ORDER BY rm.fecha_entrada DESC
            """)
            result = current_app.db.execute(query, {"tenant_id": self.tenant_id}).mappings()
            return [dict(row) for row in result]

        except Exception as e:
            return {"error": str(e)}, 500
    
    def eliminar_reserva(self, reserva_id):
        try:
            # soft-delete o eliminación real
            query = text("""
                DELETE FROM reservas_generales
                WHERE id = :reserva_id AND tenant_id = :tenant_id
            """)
            result = self.db.execute(query, {
                "reserva_id": reserva_id,
                "tenant_id": self.tenant_id
            })

            if result.rowcount == 0:
                return {"error": "Reserva no encontrada o no pertenece al negocio"}, 404

            self.db.commit()
            return {"mensaje": "Reserva eliminada correctamente"}

        except Exception as e:
            self.db.rollback()
            return {"error": str(e)}, 500